"""
Scraper of Drugs Leaflets from the ANVISA website - Search and List
================================================================================

This module performs the sequential or parallel extraction of drugs returned
by the search by category, navigating through the interface and listing them
with their URLs to get more information and download them later

Execution Flow:
    1. Connects to remote Selenium Hub (Firefox)
    2. Access the search page by regulatory categories
    3. Iterate and anotate over all results pages (CSV)
    4. Extract and save tabular data from each page (Pickle)
    5. Consolidates and saves final result (Pickle, CSV)

Prerequisites:
    - Selenium Hub running and accessible via HUB_URL
    - Firefox/Chrome nodes configured and connected to the Hub


Author: Vinícius de Lima Gonçalves
Documentation: Gemini 2.5 Pro (Student), Vinícius de Lima Gonçalves
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Tuple

from bs4 import BeautifulSoup
from filelock import FileLock
from loguru import logger
import pandas as pd
from retry import retry
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from drugslm.dataset.anvisa.config import (
    CATEGORIES,
    CATEGORIES_DIR,
    CATEGORIES_URL,
    OUTPUT_DIR,
    SEARCH_COLUMNS,
)
from drugslm.resources.selenium import get_firefox_options, managed_webdriver
from drugslm.utils.asserts import assert_text_number
from drugslm.utils.selenium import highlight, scroll

# ====== CONSTANTS ======

XPATH_PAGINATION = "//ul[contains(@class, 'pagination')]"
XPATH_current_page = f"{XPATH_PAGINATION}//li[contains(@class, 'active')]//a"
XPATH_LAST_PAGE = f"{XPATH_PAGINATION}//a[contains(@ng-switch-when, 'last')]"


# ====== Helpers (Primitives) ======


def table2data(element: WebElement) -> list:
    """
    Parses the HTML table element and extracts rows into a list of data.

    Args:
        element (WebElement): The Selenium WebElement containing the <table>.

    Returns:
        list: A list of lists [medicamento, link, empresa, expediente, data_pub].
        Returns an empty list if no table is found or parsing fails.
    """
    try:
        logger.debug("Starting table HTML parsing...")

        html = element.get_attribute("outerHTML")
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")

        if not table:
            logger.error("Parsing failed: No <table> tag found in the provided element.")
            return []

        data = []
        rows = table.find_all("tr")

        for i, tr in enumerate(rows):
            tds = tr.find_all("td")

            # Skip headers or rows without columns
            if not tds:
                continue

            if len(tds) < 5:
                logger.warning(
                    f"Skipping malformed row {i}: Expected 5+ columns, found {len(tds)}."
                )
                continue

            tds = tds[1:]

            medicamento_cell = tds[0]
            medicamento = medicamento_cell.get_text(strip=True) or None

            a_tag = medicamento_cell.find("a")
            link_medicamento = a_tag["href"] if a_tag and a_tag.has_attr("href") else None

            empresa = tds[1].get_text(strip=True) or None
            expediente = tds[2].get_text(strip=True) or None
            data_pub = tds[3].get_text(strip=True) or None

            row = [medicamento, link_medicamento, empresa, expediente, data_pub]
            data.append(row)

        logger.debug(f"Table parsed successfully. Extracted {len(data)} rows.")
        return data

    except Exception as e:
        logger.exception(f"Unexpected error while parsing table data: {e}")
        return []


@retry(tries=5, delay=2, backoff=1.2)
def get_pages(driver: WebDriver) -> Tuple[dict, WebElement]:
    """
    Captures the current state of pagination controls and the next page element.

    Retries on failure (e.g., StaleElementReferenceException, TimeoutException).

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Raises:
        TimeoutException: If the pagination container is not found.
        NoSuchElementException: If specific page elements (active/last/next) are missing.

    Returns:
        Tuple[dict, WebElement]: A tuple containing:
            - dict: A dictionary with keys 'current', 'next', and 'last' (all integers).
            - WebElement: The Selenium element corresponding to the *next* page button.
    """
    try:
        pagination = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, XPATH_PAGINATION))
        )

        current_page = pagination.find_element(By.XPATH, XPATH_current_page)
        last_page = pagination.find_element(By.XPATH, XPATH_LAST_PAGE)

        current_page_number, last_page_number, next_page_number = resolve_next_page(
            current_page, last_page
        )

        next_page = pagination.find_element(
            By.XPATH,
            f"{XPATH_PAGINATION}//li[normalize-space(.) = '{next_page_number}']//a",
        )

        logger.info(
            f"Captured pagination. Current {current_page_number}, Last {last_page_number} and Next {next_page_number} found"
        )

        return {
            "current": current_page_number,
            "next": next_page_number,
            "last": last_page_number,
        }, next_page

    except Exception as e:
        logger.error(f"Failed to get pagination details: {e}")
        raise


def resolve_next_page(current_page: WebElement, last_page: WebElement) -> Tuple[int, int, int]:
    """
    Parses pagination WebElements to extract current, last, and calculates next page numbers.

    This function validates that the text content of the elements are numeric
    before converting them. It also handles the logic to determine the next page number,
    preventing it from exceeding the last page.

    Args:
        current_page (WebElement): The WebElement representing the currently active page.
        last_page (WebElement): The WebElement representing the last available page.

    Raises:
        AssertionError: If the text of the provided elements is not numeric (via assert_text_number).
        ValueError: If conversion to integer fails.

    Returns:
        Tuple[int, int, int]: A tuple containing (current_page_num, last_page_num, next_page_num).
    """
    current_page_text = current_page.text
    assert_text_number(current_page_text)
    current_page_number = int(current_page_text)

    last_page_text = last_page.text
    assert_text_number(last_page_text)
    last_page_number = int(last_page_text)

    next_page_number = (
        current_page_number + 1 if current_page_number < last_page_number else last_page_number
    )

    return current_page_number, last_page_number, next_page_number


@retry(tries=5, delay=2, backoff=1.2)
def find_table(driver: WebDriver) -> WebElement:
    """
    Waits for the main results table to be present in the DOM.

    This function uses visual helpers (scroll and highlight) to indicate
    the found table during execution.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Returns:
        WebElement: The found <table> element.

    Raises:
        TimeoutException: If the table is not found within the timeout period (after retries).
    """
    try:
        logger.debug("Attempting to find table element...")

        table = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table")),
        )

        scroll(driver, table)
        highlight(driver, table, color="blue")

        logger.debug("Table found successfully.")
        return table

    except Exception:
        logger.error("Failed to find table after retries.")
        raise


# ====== I/O & Persistence (File Handling) ======


def save_data(data: list, category_id: int, page_num: int) -> int:
    """
    Saves a single page of scraped data to a pickle file.

    Args:
        data (list): The raw data list extracted from the table.
        category_id (int): The category ID being processed.
        page_num (int): The current page number.

    Returns:
        int: The number of rows saved.
    """
    output_path = CATEGORIES_DIR / f"{category_id}_{page_num}.pkl"

    df = pd.DataFrame(data=data, columns=SEARCH_COLUMNS)
    df.to_pickle(output_path)

    logger.info(f"Table checkpoint saved: {output_path}")
    return len(df)


def join_category_pages() -> Path:
    """
    Consolidates all individual page pickle files into a single DataFrame.

    Returns:
        Path: The path to the consolidated file, or None if no files found.
    """
    all_files = list(CATEGORIES_DIR.glob("*.pkl"))

    if not all_files:
        logger.warning("No pickle files found to consolidate in CATEGORIES_DIR.")
        return None

    # ignore_index=True recria o índice de 0 a N, evitando duplicatas de índices das páginas
    all_tables = pd.concat([pd.read_pickle(f) for f in all_files], ignore_index=True)

    all_table_path = OUTPUT_DIR / "categories_table.pkl"
    all_tables.to_pickle(all_table_path)

    logger.info(f"Consolidation complete. Saved {len(all_tables)} rows to {all_table_path}")
    return all_table_path


def save_category_pages(category_id: int, pages: dict, saved_size: int) -> None:
    """
    Appends execution metadata to a CSV file with file locking for concurrency safety.

    Args:
        category_id (int): The category ID.
        pages (dict): Pagination state dictionary {'current', 'next', 'last'}.
        saved_size (int): Number of rows saved in this step.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output = OUTPUT_DIR / "categories_tables_progress.csv"
    lock_path = output.with_suffix(".csv.lock")

    with FileLock(lock_path):
        exists = output.exists()
        with open(output, "a") as out:
            if not exists:
                out.write("category_id,timestamp,current_page,next_page,last_page,saved_size\n")

            out.write(
                f"{category_id},{timestamp},{pages['current']},{pages['next']},{pages['last']},{saved_size}\n"
            )


# ====== Core Business Logic (Process) ======


def process_category_pages(driver: WebDriver, category_id: int) -> None:
    """
    Iterates through all pages of a specific regulatory category, extracting and saving data.

    This function handles pagination navigation, saves checkpoints for every page found,
    and logs the execution progress.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The ID of the regulatory category to scrape.
    """
    url = CATEGORIES_URL % str(category_id)
    search_size = 0

    logger.info(f"Accessing ANVISA search page: {url}")
    driver.get(url)

    pages, next_button = get_pages(driver)
    logger.info(f"Pagination found. Last page: {pages['last']}")

    while pages["current"] <= pages["last"]:
        logger.info(f"Scraping page {pages['current']} of {pages['last']}...")

        table = find_table(driver)
        data = table2data(table)

        if not data:
            logger.warning(f"No data found on page {pages['current']}. Stopping category.")
            break

        saved_size = save_data(data, category_id, pages["current"])
        save_category_pages(category_id, pages, saved_size)
        search_size += saved_size

        if pages["current"] == pages["last"]:
            logger.info("Last page reached. Ending scrape.")
            break

        previous_page = pages["current"]

        scroll(driver, next_button)
        highlight(driver, next_button, color="green")

        next_button.click()
        sleep(1)

        pages, next_button = get_pages(driver)
        sleep(1)

        if previous_page == pages["current"]:
            logger.warning(
                f"Page did not change after click: {pages['current']} == {previous_page}. Stopping to avoid loop."
            )
            break

    logger.info(f"Category {category_id} processing complete. Total rows saved: {search_size}")


# ====== Orchestration (Execution) ======


def process_single_category(category_id: int) -> None:
    """
    Orchestrates the scraping of a single category.
    Manages the WebDriver lifecycle.
    """
    logger.info(f"--- Starting Process for Category {category_id} ---")

    options = get_firefox_options()

    try:
        with managed_webdriver(options) as driver:
            process_category_pages(driver, category_id)
    except Exception as e:
        logger.exception(f"Process failed for Category {category_id}: {e}")


def build_index_sequential() -> None:
    """Runs scraping sequentially for all categories."""
    for cat_id in CATEGORIES:
        process_single_category(cat_id)


def build_index_parallel(n_threads: int) -> None:
    """Runs scraping in parallel."""
    logger.info(f"Starting pool with {n_threads} workers.")
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.map(process_single_category, CATEGORIES)


# ====== SCRIPT ENTRY POINT ======

if __name__ == "__main__":
    from typing import Optional

    import typer
    from typing_extensions import Annotated

    #from drugslm.config import BROWSER_NODES
    from drugslm.utils.loguru import get_log_path, setup_logging

    BROWSER_NODES = 1

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

        log_file_path = get_log_path(__file__)
        setup_logging(log_file_path)

        threads_to_use = n_threads or BROWSER_NODES

        try:
            if parallel:
                logger.info(f"Execution mode: Parallel (n_threads={threads_to_use})")
                build_index_parallel(n_threads=threads_to_use)

            else:
                logger.info("Execution mode: Sequential")
                build_index_sequential()

            logger.info(f"Execution complete. Log: {log_file_path.resolve()}")

        except Exception as e:
            logger.exception(f"Fatal error during execution {e}. Log: {log_file_path.resolve()}")
            raise typer.Exit(code=1)

    app()
