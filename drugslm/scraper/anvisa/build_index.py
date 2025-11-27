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
from functools import partial
import logging
from time import sleep
from typing import Tuple

from bs4 import BeautifulSoup
from filelock import FileLock
import pandas as pd
from retry import retry
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from drugslm.scraper.anvisa.config import (
    CATEGORIES,
    CATEGORIES_URL,
    INDEX_DIR,
    SEARCH_COLUMNS,
)
from drugslm.scraper.selenium import get_firefox_options, highlight, scroll, webdriver_manager
from drugslm.utils.asserts import assert_text_number

logger = logging.getLogger(__name__)

# from selenium.common.exceptions import WebDriverException

# ====== CONSTANTS ======

XPATH_PAGINATION = "//ul[contains(@class, 'pagination')]"
XPATH_CURRENT_PAGE = f"{XPATH_PAGINATION}//li[contains(@class, 'active')]//a"
XPATH_LAST_PAGE = f"{XPATH_PAGINATION}//a[contains(@ng-switch-when, 'last')]"

XPATH_PAGE_COUNT = "//div[contains(@class, 'ng-table-counts')]"

# ====== OUTPUTS ======

INDEX_FETCHED = INDEX_DIR / "index_fetched.csv"
INDEX_PROGRESS = INDEX_DIR / "scrap_progress.csv"
INDEX_CHUNKS = INDEX_DIR / "chunks"
INDEX_TABLE = INDEX_DIR / "final_table.pkl"


# ====== Helpers (Primitives) ======


def set_max_pages(driver: WebDriver) -> None:
    """
    Attempts to select the highest available "items per page" option (e.g., 50).
    Iterates through options in reverse order.

    If the highest option fails, it tries the next lower one.
    This function swallows exceptions to prevent script execution stoppage.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
    """
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, XPATH_PAGE_COUNT))
        )

        buttons = container.find_elements(By.TAG_NAME, "button")

        if not buttons:
            logger.warning("Pagination count container found, but no buttons were visible.")
            return

        for btn in reversed(buttons):
            try:
                if "active" in btn.get_attribute("class"):
                    logger.info(f"Max page count already active: {btn.text}")
                    return

                btn.click()
                logger.info(f"Successfully set page count to: {btn.text}")
                return

            except WebDriverException as e:
                logger.warning(
                    f"Failed to click page count option '{btn.text}'. Trying previous option. Error: {e}"
                )
                continue

    except Exception as e:
        logger.error(f"Non-blocking error in set_max_pages: {e}")

def table2data(element: WebElement) -> list:
    """
    Parses the HTML table element and extracts rows into a list of data.

    Args:
        element (WebElement): The Selenium WebElement containing the `<table>`.

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
            logger.error("Parsing failed: No `<table>` tag found in the provided element.")
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
            - WebElement: The Selenium element corresponding to the *last* page button.
    """
    try:
        pagination = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, XPATH_PAGINATION))
        )

        current_page = pagination.find_element(By.XPATH, XPATH_CURRENT_PAGE)
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

        return (
            {
                "current": current_page_number,
                "next": next_page_number,
                "last": last_page_number,
            },
            next_page,
            last_page,
        )

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
        WebElement: The found `<table>` element.

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


def save_chuck(data: list[list], category_id: int, page_num: int) -> int:
    """
    Saves a single page of scraped data to a pickle file.

    Args:
        data (list): The raw data list extracted from the table.
        category_id (int): The category ID being processed.
        page_num (int): The current page number.

    Returns:
        int: The number of rows saved.
    """
    INDEX_CHUNKS.mkdir(parents=True, exist_ok=True)

    output_path = INDEX_CHUNKS / f"{category_id}_{page_num}.pkl"

    df = pd.DataFrame(data=data, columns=SEARCH_COLUMNS)
    df.insert(0, "id", value=category_id)
    df.insert(0, "page", value=page_num)
    df.to_pickle(output_path)

    logger.info(f"Table checkpoint saved: {output_path}")
    return len(df)

def join_chunks() -> None:
    """
    Consolidates all individual page pickle files into a single DataFrame.

    Returns:
        Path: The path to the consolidated file, or None if no files found.
    """
    all_files = list(INDEX_CHUNKS.glob("*.pkl"))

    if not all_files:
        logger.warning("No pickle files found to consolidate in {INDEX_CHUNKS}.")
        return

    logger.info(f"{len(all_files)} files found in {INDEX_CHUNKS}")

    # ignore_index=True recria o índice de 0 a N, evitando duplicatas de índices das páginas
    all_tables = pd.concat([pd.read_pickle(f) for f in all_files], ignore_index=True)

    all_tables.to_pickle(INDEX_TABLE)
    all_tables.to_csv(INDEX_TABLE.with_suffix(".csv"), index=False)

    logger.info(f"Consolidation complete. Saved {len(all_tables)} rows to {INDEX_TABLE}")

def delete_chunks():
    all_files = list(INDEX_CHUNKS.glob("*.pkl"))

    try:
        for f in all_files:
            f.unlink()

        INDEX_CHUNKS.rmdir()

        logger.info("Remove chunks files complete")
    except Exception as e:
        logger.error(f"Error to delete files: {e}")

def save_progress(category_id: int, pages: dict, saved_size: int) -> None:
    """
    Appends execution metadata to a CSV file with file locking for concurrency safety.

    Args:
        category_id (int): The category ID.
        pages (dict): Pagination state dictionary {'current', 'next', 'last'}.
        saved_size (int): Number of rows saved in this step.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    lock_path = INDEX_PROGRESS.with_suffix(".csv.lock")

    with FileLock(lock_path):
        with open(INDEX_PROGRESS, "a") as out:
            if not INDEX_PROGRESS.exists():
                out.write("category_id,timestamp,current_page,next_page,last_page,saved_size\n")

            out.write(
                f"{category_id},{timestamp},{pages['current']},{pages['next']},{pages['last']},{saved_size}\n"
            )

def get_last_progress(category_id: int):
    ## le dataframe from INDEX_PROGRESS
    ## o dataframe tem essas colunas category_id,timestamp,current_page,next_page,last_page,saved_size
    ## a ideia é que esse arquivo não seja apagado ou modificado manualmente 
    ## mas muita coisa pode ir se repetindo. 
    ## A informação mais importante no momento é qual foi a última pagina processada do category_id
    ## O timestamp vai ser usado para pegar o ultimo registro 
    return category_id

def get_index() -> pd.DataFrame:
    try:
        return pd.read_pickle(INDEX_TABLE)
    except Exception as e:
        logger.error(f"{INDEX_TABLE} doesn't exist or not could be read {e}")
        raise

def get_fetch(category_id: int | None = None) -> pd.DataFrame | int | None:
    """
    Loads the categories metadata file. Returns the whole DF or specific category size.

    Args:
        category_id (int | None): Optional ID to filter specific size.

    Returns:
        pd.DataFrame | int | None: DataFrame if no ID passed, int if ID found, None if file missing.
    """

    if not INDEX_FETCHED.exists():
        logger.warning(f"Fetch file not found at {INDEX_FETCHED}. Returning None.")
        return None

    try:
        df = pd.read_csv(INDEX_FETCHED)

        if category_id is None:
            logger.info(f"Loaded fetched categories metadata ({len(df)} records).")
            return df

        # Filter for specific category
        row = df.loc[df["id"] == category_id, "size"]

        if row.empty:
            logger.warning(f"Category {category_id} not found in fetch file.")
            return None

        return int(row.iloc[0]) !!! ta estranho

    except Exception as e:
        logger.error(f"Error reading fetched categories CSV: {e}")
        return None

def check_index() -> int:
    """
    Checks the consistency between the local index and the ANVISA database.

    Modes:
    - keep=True: Compares local index with *stored* metadata (verifies integrity of the last run).
    - keep=False: Fetches *fresh* metadata from ANVISA and compares with local index (checks for updates).

    Args:
        keep (bool): Whether to use existing metadata (True) or fetch fresh data (False).
    """
    logger.info(f"--- Starting Index Check ---")

    # 1. Carrega o índice local (O que nós temos)
    try:
        df_local = get_index()
        local_size = len(df_local)
        logger.info(f"Local index found: {local_size} records.")
    except Exception:
        logger.warning("Local index (final_table) not found or unreadable.")
        local_size = 0


    logger.info("Loading stored metadata (verifying previous run integrity)...")
    df_meta = get_fetch()

    if df_meta is None:
        logger.error("Could not obtain metadata for comparison.")
        return

    expected_size = int(df_meta["size"].sum())

    # 3. Comparação e Relatório
    diff = expected_size - local_size

    logger.info("=" * 40)
    logger.info(f"EXPECTED: {expected_size}")
    logger.info(f"FOUND: {local_size}")
    logger.info("=" * 40)

    if diff == 0:
        logger.info("Local index is complete.")
    elif diff > 0:
        logger.warning(f"Missing {diff} records.")
    else:
        logger.warning(f"Local index has {-diff} more records than fetched.")

    return diff

# ====== Scraper Core Business Logic (Process) ======


def scrap_pages(driver: WebDriver, category_id: int, remain: bool = False) -> None:
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


    # ? preciso do remain? não é melhor olhar o progress ou os chunks e ver sozinho? 
    # até pq se remain == false os chunks já foram apagados
    # supondo que a categoria tem 50 páginas e dessas 30 foram
    # initial_page = get_remained_pages(category_id) | 1
    #

    logger.info(f"Accessing ANVISA search page: {url}")
    driver.get(url)

    set_max_pages(driver)

    pages, next_button, _ = get_pages(driver)
    logger.info(f"Pagination found. Last page: {pages['last']}")

    while pages["current"] <= pages["last"]:
        logger.info(f"Scraping page {pages['current']} of {pages['last']}...")

        table = find_table(driver)
        data = table2data(table)

        if not data:
            logger.warning(f"No data found on page {pages['current']}. Stopping category.")
            break

        saved_size = save_chuck(data, category_id, pages["current"])
        save_progress(category_id, pages, saved_size)
        search_size += saved_size

        if pages["current"] == pages["last"]:
            logger.info("Last page reached. Ending scrape.")
            break

        previous_page = pages["current"]

        scroll(driver, next_button)
        highlight(driver, next_button, color="green")

        next_button.click()
        sleep(1)

        pages, next_button, _ = get_pages(driver)
        sleep(1)

        if previous_page == pages["current"]:
            logger.warning(
                f"Page did not change after click: {pages['current']} == {previous_page}. Stopping to avoid loop."
            )
            break

    logger.info(f"Category {category_id} processing complete. Total rows saved: {search_size}")

    return pages["current"], search_size

def scrap_unit_category(category_id: int, keep: bool = False) -> None:
    """
    Orchestrates the scraping of a single category with pre-fetch validation.
    """
    logger.info(f"--- Starting Process for Category {category_id} ---")

    ############################################ better place it in scrape_pages
    # Check against fetched metadata
    expected_size = get_fetch(category_id)

    if expected_size is None:
        logger.info(f"No fetch metadata available for Category {category_id}. Proceeding blindly.")
    elif expected_size == 0:
        logger.warning(f"Skipping Category {category_id}: Fetch indicates 0 items.")
        return
    else:
        logger.info(f"Category {category_id}: Expecting {expected_size} items.")
    #
    ###########################
    # Pensei em duas saídas:
    ## nesse ponto tem get_fetch(category_id) e o keep
    ## aqui já é possível descobrir se a categoria vai retornar algo
    ## e também é possível saber quantos que vai ser retornado
    ## com esse número é possível verificar se pegou tudo ou não
    ## mas não é possível verificar em qual página parou
    ## posso olhar o diretorio de chuck e procurar pelos arquivos
    ## mas não é melhor fazer isso usando o csv de progresso?
    ## (considerar ter valores (category,page) únicos? considerar o ultimo dado o timestamp)    




    options = get_firefox_options()

    try:
        with webdriver_manager(options) as driver:
            scrap_pages(driver, category_id, keep)
    except Exception as e:
        logger.exception(f"Process failed for Category {category_id}: {e}")


# ====== Fetch Core Business Logic (Process) ======


def fetch_unit_category(driver: WebDriver, category_id: int) -> list: #<---------- PAREI AS ALTERAÇÕES COM O GEMINI. Acho que não preciso mexer em nada
    """
    Navigates to the first and last page of a category to estimate data volume.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The regulatory category ID.

    Returns:
        list: [category_id, total_pages, estimated_total_items].
    """
    url = CATEGORIES_URL % str(category_id)
    logger.info(f"Fetching metadata for Category {category_id} | URL: {url}")

    driver.get(url)

    try:
        pages, _, last_button = get_pages(driver)
    except Exception:
        logger.warning(f"Category {category_id}: Pagination not found or empty. Assuming 0 items.")
        return [category_id, 0, 0]

    table1 = find_table(driver)
    data1 = table2data(table1)
    page_size = len(data1)

    if pages["last"] > 1:
        logger.debug(f"Category {category_id}: Jumping to last page ({pages['last']})...")
        last_button.click()
        sleep(1)

        table2 = find_table(driver)
        data2 = table2data(table2)
        last_page_items = len(data2)
    else:
        last_page_items = page_size

    total_items = ((pages["last"] - 1) * page_size) + last_page_items

    logger.info(
        f"Category {category_id} Stats: Pages={pages['last']} | "
        f"PageSize={page_size} | Total={total_items}"
    )

    return [
        category_id,
        pages["last"],
        total_items,
    ]



# ====== Orchestration (Execution) ======


def scrap_categories(n_threads: int = 1, remain: bool = False):
    """
    Orchestrates the parallel scraping of all categories.

    Manages the lifecycle of the scraping process:
    1. Prepares the environment (cleans chunks if not in 'keep' mode).
    2. Distributes scraping tasks across a thread pool.
    3. Consolidates results into a single file.
    4. Validates data integrity and performs final cleanup.

    Args:
        n_threads (int): Number of concurrent threads to use. Defaults to 1.
        keep (bool): If True, retains previous temporary chunks to resume execution. 
                     If False, starts fresh by clearing old chunks.
    """
    logger.info(
        f"--- Starting Scraping Pipeline (Threads: {n_threads}, Keep: {remain}) ---"
    )


    if not remain:
        logger.info("keep=False: Clearing previous temporary chunks before starting.")
        delete_chunks()
        # delete progress file


    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.map(
            partial(
                scrap_unit_category,
                remain=remain, # se tudo já foi apagado, caso remain == false, tem pq passar isso adiante?
            ),
            CATEGORIES,
        )

    logger.info("Thread pool execution finished. Consolidating data chunks and check final data...")
    join_chunks()
    
    result = check_index()

    if result == 0:
        # logger.info
        delete_chunks()

    logger.info(f"Scraping Pipeline Finished with {result} remained")

def fetch_categories():
    """
    Orchestrates metadata fetching for all categories listed in CATEGORIES.
    """

    options = get_firefox_options()
    logger.info("--- Setup Fetch Execution ---")

    fetch_columns = [
        "id",
        "pages",
        "size",
    ]
    fetch_values = []

    logger.info("--- Starting Fetch Routine for All Categories ---")

    try:
        for category_id in CATEGORIES:
            try:
                with webdriver_manager(options) as driver:
                    stats = fetch_unit_category(driver, category_id)
                    fetch_values.append(stats)
            except Exception as e:
                logger.error(f"Failed to fetch metadata for Category {category_id}: {e}")
                fetch_values.append([category_id, 0, 0])

        fetch_df = pd.DataFrame(fetch_values, columns=fetch_columns)
        fetch_df.to_csv(INDEX_FETCHED, index=False)

        logger.info(f"Fetch complete. Metadata saved to {INDEX_FETCHED}")

    except Exception as e:
        logger.critical(f"Critical error during categories fetch: {e}")
        raise


# ====== SCRIPT ENTRY POINT ======

if __name__ == "__main__":
    import typer
    from typing_extensions import Annotated

    from drugslm.utils.logging import get_log_path, setup_logging

    log_file_path = get_log_path(__file__)
    setup_logging(log_file_path)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    app = typer.Typer(
        help="CLI for get drug informations from ANVISA.",
        # pretty_exceptions_show_locals=False,
        # add_completion=False,
    )

    @app.command()
    def run(
        n_threads: Annotated[
            int,
            typer.Option(
                "--threads",
                "-t",
                help="Number of threads for parallel processing.",
                min=1,
                max=len(CATEGORIES),
                show_default=True,
            ),
        ] = 1,
        remain: Annotated[
            bool,
            typer.Option(
                "--remain",
                "-r",
                help="Keep previous execution data (do not start from zero).",
                show_default=False,
            ),
        ] = False,
        check: Annotated[
            bool,
            typer.Option(
                "--check",
                "-c",
                help="Only check execution status/updates. Uses --keep logic to decide between fresh fetch or local metadata.",
                show_default=False,
            ),
        ] = False,
        update: Annotated[
            bool,
            typer.Option(
                "--update",
                "-u",
                help="",
                show_default=True,

            )
        ] = True
    ):
        """
        Runs the ANVISA drug listing scraper pipeline.
        """

        try:
            if update:
                fetch_categories()

            if check:
                check_index(update)
                return

            # Modo Pipeline Padrão
            logger.info(f"Starting pipeline (Threads: {n_threads}, Keep: {remain})...")
    
            scrap_categories(n_threads, remain, update)

            logger.info(f"Pipeline execution complete. Log: {log_file_path.resolve()}")

        except Exception as e:
            logger.exception(f"Fatal error during pipeline execution: {e}")
            raise typer.Exit(code=1)

    app()