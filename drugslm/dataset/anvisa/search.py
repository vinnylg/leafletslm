"""
Scraper of Drugs Leaflets from the ANISA website - Search and List
================================================================================

This module performs the sequential or parallel extraction of drugs returned
by the search by category, navigating through the interface and listing them
with their URLs to get more informations and download them later

Execution Flow:
    1. Connects to remote Selenium Hub (Firefox)
    2. Access the search page by regulatory categories
    3. Iterate over all results pages
    4. Extract tabular data from each page
    5. Consolidates and saves final result (Pickle, CSV)

Prerequisites:
    - Selenium Hub running and accessible via HUB_URL
    - Firefox/Chrome nodes configured and connected to the Hub


Author: Vinícius de Lima Gonçalves
Documentation: Gemini 2.5 Pro (Student), Vinícius de Lima Gonçalves
"""

from pathlib import Path
from time import sleep
from typing import List, Tuple

from bs4 import BeautifulSoup
import pandas as pd
from retry import retry
from selenium.common.exceptions import JavascriptException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from drugslm.dataset.anvisa.config import CATEGORIAS, CATEGORIES_URL, OUTPUT_DIR, SEARCH_COLUMNS
from loguru import logger

# ====== CONSTANTS ======

XPATH_PAGINATION = "//ul[contains(@class, 'pagination')]"
XPATH_ACTIVE_PAGE = f"{XPATH_PAGINATION}//li[contains(@class, 'active')]//a"
XPATH_LAST_PAGE = f"{XPATH_PAGINATION}//a[contains(@ng-switch-when, 'last')]"


# ======= ASSERTS =============


def assert_text_number(elem: str) -> None:
    """
    Valida que o valor do elemento é uma string numérica.

    Args:
        elem: Valor textual da página.

    Raises:
        AssertionError: Se o valor não for string ou não for numérico.
    """
    assert isinstance(elem, str), "Elemento não é uma string"
    assert elem.isnumeric(), "Elemento não é um valor numérico"


# ====== Debuggers (Visualize) ======


def highlight(driver: WebDriver, element: WebElement, color: str = "green") -> None:
    """Highlights a specific WebElement by drawing a border around it.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        element (WebElement): The target Selenium WebElement instance.
        color (str, optional): The colour to highlight. Defaults to "green".
    """
    try:
        driver.execute_script(f"arguments[0].style.border='3px solid {color}';", element)
        sleep(1)

    except JavascriptException:
        pass  #! Fail silently if highlighting isn't critical


def scroll_to_element(driver: WebDriver, element: WebElement) -> None:
    """Scrolls the page to bring the specified WebElement into view.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        element (WebElement): The target Selenium WebElement instance.
    """
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element
        )
        sleep(1)

    except JavascriptException:
        pass  #! Fail silently


# ====== Helpers (Primitives) ======


def table2df(element: WebElement) -> list:
    html = element.get_attribute("outerHTML")
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    if not table:
        # log_message(message_type="no_table_found")
        raise ValueError("Nenhuma tabela encontrada no elemento informado.")

    data = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        # Ignora o primeiro <td> (checkbox)
        tds = tds[1:]
        medicamento_cell = tds[0]
        medicamento = medicamento_cell.get_text(strip=True) or None
        a_tag = medicamento_cell.find("a")
        link_medicamento = a_tag["href"] if a_tag and a_tag.get("href") else None

        empresa = tds[1].get_text(strip=True) or None
        expediente = tds[2].get_text(strip=True) or None
        data_pub = tds[3].get_text(strip=True) or None

        row = [medicamento, link_medicamento, empresa, expediente, data_pub]
        data.append(row)

    # log_message(message_type="table_extracted", rows=len(data))

    return data


@retry(tries=5, delay=2, backoff=1.2)
def get_pages(driver: WebDriver) -> Tuple[int, int, WebElement]:
    """
    Gets the current state of the pagination controls.
    Retries on failure.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Raises:
        e: _description_

    Returns:
        Tuple[int, int, WebElement]: (current_page_num, last_page_num, next_page_element)
    """
    try:
        pagination = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, XPATH_PAGINATION))
        )

        active_page = pagination.find_element(By.XPATH, XPATH_ACTIVE_PAGE)
        last_page = pagination.find_element(By.XPATH, XPATH_LAST_PAGE)

        active_page_number, last_page_number, next_page_number = get_pages_number(
            active_page, last_page
        )

        next_page = pagination.find_element(
            By.XPATH,
            f"{XPATH_PAGINATION}//li[normalize-space(.) = '{next_page_number}']//a",
        )

        logger.info(
            f"Captured pagination. Current {active_page_number}, Last {last_page_number} and Next {next_page_number} found"
        )
    except Exception as e:
        logger.error(f"Failed to get pagination details: {e}")
        raise e

    return int(active_page_number), int(last_page_number), next_page


def get_pages_number(active_page: WebElement, last_page: WebElement) -> Tuple[int, int, int]:
    active_page_text = active_page.text
    assert_text_number(active_page_text)
    active_page_number = int(active_page_text)

    last_page_text = last_page.text
    assert_text_number(last_page_text)
    last_page_number = int(last_page_text)

    next_page_number = (
        active_page_number + 1 if active_page_number < last_page_number else last_page_number
    )

    return active_page_number, last_page_number, next_page_number


@retry(tries=5, delay=2, backoff=1.2)
def find_table(driver: WebDriver) -> None:
    """
    Waits for the main results table to be present.
    Retries on failure.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Raises:
        e: _description_
    """
    try:
        logger.debug("Attempting to find table element...")

        table = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table")),
        )
        scroll_to_element(driver, table)
        highlight(driver, table, color="blue")

        logger.debug("Table found")
        return table

    except Exception as e:
        logger.error(f"Failed to find table after retries: {e}")
        raise e


# ====== I/O & Persistence (File Handling) ======


def save_anvisa_scraped(data: list, categories: List[int] = CATEGORIAS) -> Path:
    categories_str = "_".join([str(c) for c in categories])
    df = pd.DataFrame(data=data, columns=SEARCH_COLUMNS)
    df.insert(0, "categories", categories)
    df.to_pickle(OUTPUT_DIR / f"categories_{categories_str}.pkl")
    return OUTPUT_DIR / f"categories_{categories_str}.pkl"


def join_anvisa_scraped() -> str:
    None


# ====== Core Business Logic (Process) ======


def scrape_anvisa_category(
    driver: WebDriver,
    url: str,
    categories: List[int] = CATEGORIAS,
) -> list:
    """
    Performs complete scraping of the medication list with pagination.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        categories (List[int]): A list of category IDs to scrape.

    Returns:
        list: A list of lists containing the scraped raw data.
    """
    url = CATEGORIES_URL % ",".join([str(c) for c in categories])

    search_list = []

    logger.info(f"Accessing ANVISA search page {url}")
    driver.get(url)

    current_page_num, last_page_num, next_page = get_pages(driver)
    logger.info(f"Pagination found. Last page: {last_page_num}")

    while current_page_num <= last_page_num:
        # 1
        logger.info(f"Scraping page {current_page_num} of {last_page_num}...")

        table = find_table(driver)
        data = table2df(table)

        if not data:
            logger.warning(f"No data found on page {current_page_num}. Stopping.")
            # go to 1
            break

        search_list.extend(data)

        if current_page_num >= last_page_num:
            logger.info("Last page reached. Ending scrape.")
            break

        previous_page = current_page_num

        # 2

        scroll_to_element(driver, next_page)
        highlight(driver, next_page, color="green")

        next_page.click()
        sleep(1)

        current_page_num, last_page_num, next_page = get_pages(driver)
        sleep(1)

        if previous_page == current_page_num:
            logger.warning(f"Page not change, {current_page_num} == {previous_page}. Stopping.")
            # go to 2
            break

    logger.info(f"Scraping complete. Total rows found: {len(search_list)}")
    return search_list


# ====== Orchestration (Execution) ======


def get_search_list_sequential() -> None:
    None


def get_search_list_parallel() -> None:
    None


# ====== SCRIPT ENTRY POINT ======

if __name__ == "__main__":
    from datetime import datetime
    import os
    from typing import Optional

    import typer
    from typing_extensions import Annotated

    from drugslm.config import BROWSER_NODES, LOG_DIR
    from drugslm.dataset.anvisa.config import get_anvisa_log_path
    from drugslm.dataset.anvisa.search import get_search_list_parallel, get_search_list_sequential
    from drugslm.loguru import setup_logging

    app = typer.Typer(
        help="CLI for scraping drug data from ANVISA.",
        pretty_exceptions_show_locals=False,
    )

    @app.command()
    def run(
        parallel: Annotated[
            bool,
            typer.Option(
                "--parallel",
                help="Run extraction in parallel. (Default: sequential)",
            ),
        ] = False,
        n_threads: Annotated[
            Optional[int],
            typer.Option(
                "--nthreads",
                help=f"Number of BROWSERS for parallel mode. (Default: {BROWSER_NODES} from BROWSER_NODES)",
                min=1,
            ),
        ] = None,
    ):
        """
        Runs the ANVISA drug listing scraper.
        """

        LOG_MODULE_NAME = "drugslm.dataset.anvisa.search"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = LOG_DIR / LOG_MODULE_NAME.replace(".", os.path.sep) / f"{timestamp}.log"

        logger = setup_logging(get_anvisa_log_path("search"))

        threads_to_use = n_threads or BROWSER_NODES

        try:
            if parallel:
                logger.info(f"Execution mode: Parallel (n_threads={threads_to_use})")
                get_search_list_parallel(n_threads=threads_to_use)

            else:
                logger.info("Execution mode: Sequential")
                get_search_list_sequential()

            logger.info(f"Execution complete. Log: {log_file_path.resolve()}")

        except Exception as e:
            logger.exception(f"Fatal error during execution {e}. Log: {log_file_path.resolve()}")
            raise typer.Exit(code=1)

    app()
