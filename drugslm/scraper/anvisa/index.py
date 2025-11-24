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
import logging
from pathlib import Path
from time import sleep
from typing import Tuple

from bs4 import BeautifulSoup
from filelock import FileLock
import pandas as pd
from retry import retry
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from drugslm.scraper.anvisa.config import (
    CATEGORIES,
    CATEGORIES_URL,
    INDEX_DIR,
    OUTPUT_DIR,
    SEARCH_COLUMNS,
)
from drugslm.scraper.selenium import get_firefox_options, highlight, scroll, webdriver_manager
from drugslm.utils.asserts import assert_text_number

logger = logging.getLogger(__name__)

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
            - WebElement: The Selenium element corresponding to the *last* page button.
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
    output_path = INDEX_DIR / f"{category_id}_{page_num}.pkl"

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
    all_files = list(INDEX_DIR.glob("*.pkl"))

    if not all_files:
        logger.warning("No pickle files found to consolidate in INDEX_DIR.")
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
    output = INDEX_DIR / "index_progress.csv"
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


def scrap_pages(driver: WebDriver, category_id: int) -> None:
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

    pages, next_button, _ = get_pages(driver)
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

        pages, next_button, _ = get_pages(driver)
        sleep(1)

        if previous_page == pages["current"]:
            logger.warning(
                f"Page did not change after click: {pages['current']} == {previous_page}. Stopping to avoid loop."
            )
            break

    logger.info(f"Category {category_id} processing complete. Total rows saved: {search_size}")

    return pages["current"], search_size


def fetch_category_page(driver: WebDriver, category_id: int) -> list:
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


def fetch_categories(driver: WebDriver) -> pd.DataFrame:
    """
    Orchestrates metadata fetching for all categories listed in CATEGORIES.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Returns:
        pd.DataFrame: DataFrame containing statistics for all categories.
    """
    fetch_columns = [
        "category_id",
        "npages",
        "category_size",
    ]
    fetch_values = []
    output_path = INDEX_DIR / "fetched_categories.csv"

    logger.info("--- Starting Fetch Routine for All Categories ---")

    try:
        for category_id in CATEGORIES:
            try:
                stats = fetch_category_page(driver, category_id)
                fetch_values.append(stats)
            except Exception as e:
                logger.error(f"Failed to fetch metadata for Category {category_id}: {e}")
                # Fallback: id, 0 pages, 0 size
                fetch_values.append([category_id, 0, 0])

        fetch_df = pd.DataFrame(fetch_values, columns=fetch_columns)
        fetch_df.to_csv(output_path, index=False)

        logger.info(f"Fetch complete. Metadata saved to {output_path}")
        return fetch_df

    except Exception as e:
        logger.critical(f"Critical error during categories fetch: {e}")
        return None


def get_fetched(category_id: int | None = None) -> pd.DataFrame | int | None:
    """
    Loads the categories metadata file. Returns the whole DF or specific category size.

    Args:
        category_id (int | None): Optional ID to filter specific size.

    Returns:
        pd.DataFrame | int | None: DataFrame if no ID passed, int if ID found, None if file missing.
    """
    file_path = INDEX_DIR / "fetched_categories.csv"

    if not file_path.exists():
        logger.warning(f"Fetch file not found at {file_path}. Returning None.")
        return None

    try:
        df = pd.read_csv(file_path)

        if category_id is None:
            logger.info(f"Loaded fetched categories metadata ({len(df)} records).")
            return df

        # Filter for specific category
        row = df.loc[df["category_id"] == category_id, "category_size"]

        if row.empty:
            logger.warning(f"Category {category_id} not found in fetch file.")
            return None

        return int(row.iloc[0])

    except Exception as e:
        logger.error(f"Error reading fetched categories CSV: {e}")
        return None


# ====== Orchestration (Execution) ======


def execute_fetch() -> pd.DataFrame | None:
    """
    Manages the WebDriver lifecycle for the fetch step.
    """
    options = get_firefox_options()
    logger.info("--- Setup Fetch Execution ---")

    try:
        with webdriver_manager(options) as driver:
            return fetch_categories(driver)
    except Exception as e:
        logger.critical(f"Fatal error during fetch execution wrapper: {e}")
        return None


def process_category(category_id: int) -> None:
    """
    Orchestrates the scraping of a single category with pre-fetch validation.
    """
    logger.info(f"--- Starting Process for Category {category_id} ---")

    # Check against fetched metadata
    expected_size = get_fetched(category_id)

    if expected_size is None:
        logger.info(f"No fetch metadata available for Category {category_id}. Proceeding blindly.")
    elif expected_size == 0:
        logger.warning(f"Skipping Category {category_id}: Fetch indicates 0 items.")
        return
    else:
        logger.info(f"Category {category_id}: Expecting {expected_size} items.")

    options = get_firefox_options()

    try:
        with webdriver_manager(options) as driver:
            scrap_pages(driver, category_id)
    except Exception as e:
        logger.exception(f"Process failed for Category {category_id}: {e}")


def process_categories(n_threads: int = 1):
    """
    Runs scraping in n_threads using a ThreadPoolExecutor.

    This acts as a dynamic load balancer: as soon as a thread finishes
    a category, it picks up the next available one from the queue.

    Args:
        n_threads (int, optional): Number of Thread to split. Defaults to 1.
    """
    if n_threads <= 0:
        n_threads = 1
    elif n_threads > len(CATEGORIES):
        n_threads = len(CATEGORIES)

    logger.info(f"Starting pool with {n_threads} workers for {len(CATEGORIES)} categories.")

    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.map(process_category, CATEGORIES)


# ====== SCRIPT ENTRY POINT ======

if __name__ == "__main__":
    import typer
    from typing_extensions import Annotated

    from drugslm.utils.logging import get_log_path, setup_logging

    # Configuração inicial de Logs
    log_file_path = get_log_path(__file__)
    setup_logging(log_file_path)

    app = typer.Typer(
        help="CLI for scraping drug data from ANVISA.",
        pretty_exceptions_show_locals=False,
        add_completion=False,
    )

    @app.command()
    def run(
        n_threads: Annotated[
            int,
            typer.Option(
                "--threads",
                "-t",
                help="Number of threads for parallel processing (Process Step only).",
                min=1,
                max=len(CATEGORIES),
                show_default=True,
            ),
        ] = 1,
        only_fetch: Annotated[
            bool,
            typer.Option(
                "--only-fetch",
                "-o",
                help="EXECUTE ONLY FETCH: Runs metadata fetching and exits.",
                show_default=False,
            ),
        ] = False,
        skip_fetch: Annotated[
            bool,
            typer.Option(
                "--skip-fetch",
                "-s",
                help="EXECUTE ONLY PROCESS: Skips metadata fetching and uses existing CSV.",
                show_default=False,
            ),
        ] = False,
    ):
        """
        Runs the ANVISA drug listing scraper pipeline.

        Modes:
        1. Default: Fetch Metadata -> Scrape Data
        2. --only-fetch (-o): Fetch Metadata -> Stop
        3. --skip-fetch (-s): Skip Metadata -> Scrape Data
        """

        if only_fetch and skip_fetch:
            logger.error(
                "Ambiguous command: You cannot use --only-fetch (-o) and --skip-fetch (-s) simultaneously."
            )
            raise typer.Exit(code=1)

        try:
            if not skip_fetch:
                logger.info("STEP 1: Fetching Categories Metadata...")
                execute_fetch()
            else:
                logger.info("STEP 1: Skipped (User Request: --skip-fetch).")

            if only_fetch:
                logger.info("Execution finished (--only-fetch selected).")
                raise typer.Exit(code=0)

            mode_label = "Parallel" if n_threads > 1 else "Sequential"
            logger.info(
                f"STEP 2: Processing Categories (Mode: {mode_label}, Threads: {n_threads})..."
            )

            process_categories(n_threads)

            join_category_pages()

            logger.info(f"Pipeline execution complete. Log: {log_file_path.resolve()}")

        except typer.Exit:
            raise
        except Exception as e:
            logger.exception(f"Fatal error during pipeline execution: {e}")
            raise typer.Exit(code=1)

    app()
