"""
Scraper of Drugs Leaflets from the ANVISA website - Search and List
================================================================================

This module performs the sequential or parallel extraction of drugs returned
by the search by category, navigating through the interface and listing them
with their URLs to get more information and download them later.

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
Documentation: Gemini 3.0 Pro (Student), Vinícius de Lima Gonçalves
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
import typer
from typing_extensions import Annotated

from drugslm.scraper.anvisa.config import (
    CATEGORIES,
    CATEGORIES_URL,
    FETCH_COLUMNS,
    INDEX_DIR,
    SEARCH_COLUMNS,
)
from drugslm.scraper.selenium import get_firefox_options, highlight, scroll, webdriver_manager
from drugslm.utils.asserts import assert_text_number

logger = logging.getLogger(__name__)

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


def set_max_table_size(driver: WebDriver) -> int:
    """
    Attempts to select the highest available "items per page" option (e.g., 50).
    Iterates through options in reverse order.

    If the highest option fails, it tries the next lower one.
    This function swallows exceptions to prevent script execution stoppage.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Returns:
        int: The selected page size. Returns 0 if failed.
    """
    try:
        container = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, XPATH_PAGE_COUNT))
        )

        buttons = container.find_elements(By.TAG_NAME, "button")

        if not buttons:
            logger.warning("Pagination count container found, but no buttons were visible.")
            return 0

        for btn in reversed(buttons):
            try:
                txt_val = btn.text.strip()
                if "active" in btn.get_attribute("class"):
                    logger.info(f"Max page count already active: {txt_val}")
                    return int(txt_val)

                btn.click()
                logger.info(f"Successfully set page count to: {txt_val}")
                return int(txt_val)

            except WebDriverException as e:
                logger.warning(
                    f"Failed to click page count option '{btn.text}'. Trying previous option. Error: {e}"
                )
                continue
        return 0

    except Exception as e:
        logger.critical(f"Element for set_max_table_size not found: {e}")
        return 0


def table2data(element: WebElement) -> list:
    """
    Parses the HTML table element and extracts rows into a list of data.

    Args:
        element (WebElement): The Selenium WebElement containing the `<table>`.

    Returns:
        list: A list of lists [medicamento, link, empresa, expediente, data_pub] or an empty list [].
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
    current_page_text = current_page.text.strip()
    assert_text_number(current_page_text)
    current_page_number = int(current_page_text)

    last_page_text = last_page.text.strip()
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


def save_chuck(raw_data: list[list], category_id: int, page_num: int) -> int:
    """
    Saves a single page of scraped data to a pickle file.

    Args:
        raw_data (list): The raw data list extracted from the table.
        category_id (int): The category ID being processed.
        page_num (int): The current page number.

    Returns:
        int: The number of rows saved.
    """
    INDEX_CHUNKS.mkdir(parents=True, exist_ok=True)

    output_path = INDEX_CHUNKS / f"{category_id}_{page_num}.pkl"

    full_data = [[category_id, page_num] + row for row in raw_data]

    df = pd.DataFrame(data=full_data, columns=SEARCH_COLUMNS)
    df.to_pickle(output_path)

    logger.info(f"Table checkpoint saved: {output_path}")
    return len(df)


def join_chunks(force: bool = False) -> None:
    """
    Consolidates all individual page pickle files into a single DataFrame.

    Args:
        force (bool): If True, completely overwrites the existing index file.
                      If False, merges new chunks with the existing index,
                      deduplicating based on the 'expediente' column.
    """

    all_files = list(INDEX_CHUNKS.glob("*.pkl"))

    if not all_files:
        logger.warning(f"No pickle files found to consolidate in {INDEX_CHUNKS}.")
        return

    logger.info(f"{len(all_files)} chunks found. Starting consolidation...")

    try:
        new_data = pd.concat([pd.read_pickle(f) for f in all_files], ignore_index=True)

        if force or not INDEX_TABLE.exists():
            logger.info("Overwriting final table.")
            final_df = new_data
        else:
            logger.info("Merging new chunks with existing index.")
            try:
                old_data = pd.read_pickle(INDEX_TABLE)

                combined = pd.concat([old_data, new_data])

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                combined.loc[
                    combined.duplicated(
                        ["expediente"],
                        keep=False,
                    )
                ].to_pickle(INDEX_DIR / f"debug_dup_{timestamp}.pkl")

                logger.info("Deduplicating based on 'expediente' keeping last")
                final_df = combined.drop_duplicates(
                    subset=["expediente"],
                    keep="last",
                )

            except Exception as e:
                logger.error(
                    f"Failed to merge with existing table, falling back to overwrite: {e}"
                )
                final_df = new_data

        # Save Final Result
        final_df.to_pickle(INDEX_TABLE)
        final_df.to_csv(INDEX_TABLE.with_suffix(".csv"), index=False)

        logger.info(f"Consolidation complete. Saved {len(final_df)} rows to {INDEX_TABLE}")

        # Only delete chunks if consolidation was successful
        delete_chunks()

    except Exception as e:
        logger.error(f"Critical error during join_chunks: {e}")


def delete_chunks(category_id: int | None = None) -> None:
    """
    Deletes temporary chunk files.

    Args:
        category_id (int | None): If provided, deletes only chunks for that category.
                                  If None, deletes all chunks.
    """
    # Use glob pattern to match specific category or all files
    pattern = f"{category_id}_*.pkl" if category_id else "*.pkl"
    all_files = list(INDEX_CHUNKS.glob(pattern))

    if not all_files:
        logger.debug(f"No chunks found to delete for pattern: {pattern}")
        return

    try:
        for f in all_files:
            f.unlink()

        # Try to remove dir if empty and we are cleaning everything
        if category_id is None and not any(INDEX_CHUNKS.iterdir()):
            INDEX_CHUNKS.rmdir()

        logger.info(f"Deleted {len(all_files)} chunk files.")
    except Exception as e:
        logger.error(f"Error deleting chunk files: {e}")


def save_progress(category_id: int, pages: dict, saved_size: int) -> None:
    """
    Appends execution metadata to a CSV file with file locking for concurrency safety.

    Args:
        category (int): The category ID.
        pages (dict): Pagination state dictionary {'current', 'next', 'last'}.
        saved_size (int): Number of rows saved in this step.
    """
    lock_path = INDEX_PROGRESS.with_suffix(".csv.lock")

    with FileLock(lock_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        with open(INDEX_PROGRESS, "a") as out:
            if not INDEX_PROGRESS.exists() or INDEX_PROGRESS.stat().st_size == 0:
                out.write("timestamp,category_id,current_page,last_page,saved_size\n")

            out.write(
                f"{timestamp},{category_id},{pages['current']},{pages['last']},{saved_size}\n"
            )


def get_index() -> pd.DataFrame | None:
    """Loads the final consolidated index. Returns empty DataFrame if not found.

    Returns:
        pd.DataFrame: consolidated index DataFrame
        None: if file is missing
    """
    try:
        df = pd.read_pickle(INDEX_TABLE)
        if not df.empty:
            return df

    except FileNotFoundError:
        logger.warning(f"Index table {INDEX_TABLE} not found. Returning None.")
    except Exception as e:
        logger.error(f"Error reading index table: {e}")


def get_fetch(category_id: int | None = None) -> pd.DataFrame | None:
    """
    Loads the categories metadata file. Returns the whole DF or specific category size.

    Args:
        category_id (int | None): Optional ID to filter specific size.

    Returns:
        pd.DataFrame: All DataFrame or filter if category_id passed
        None: If not found or error
    """

    if not INDEX_FETCHED.exists():
        logger.warning(f"Fetch file not found at {INDEX_FETCHED}. Returning None.")
        return None

    try:
        df = pd.read_csv(INDEX_FETCHED)

        if category_id is None:
            logger.info(f"Loaded fetched categories metadata ({len(df)} records).")
            return df if not df.empty else None

        row = df.loc[df["category_id"] == category_id]

        if row.empty:
            logger.warning(f"Category {category_id} not found in fetch file.")
            return None

        return row

    except Exception as e:
        logger.error(f"Error reading fetched categories CSV: {e}")
        return None


def check_index(category_id: int | None = None) -> int:
    """
    Checks the consistency between the local index and the ANVISA database.

    Args:
        category_id (int | None): ID to check specific category consistency.
                                  If None, checks global consistency.
    """
    logger.info(
        f"--- Starting Index Check (Target: {category_id if category_id else 'Global'}) ---"
    )

    if (df_local := get_index()) is None:
        logger.error("Could not obtain local index for comparison.")
        return -1

    if category_id:
        df_local = df_local[df_local["category_id"] == category_id]

    local_size = len(df_local)
    logger.info(f"Local index found: {local_size} records.")

    if (df_meta := get_fetch(category_id)) is None:
        logger.error("Could not obtain metadata for comparison.")
        return -1

    expected_size = df_meta["num_items"].sum()
    diff = expected_size - local_size

    logger.info("--- Index Consistency Report ---")
    logger.info(f"Expected (Remote) : {expected_size:>8}")
    logger.info(f"Found    (Local)  : {local_size:>8}")
    logger.info(f"Difference        : {diff:>8}")
    logger.info("-" * 34)

    if diff == 0:
        logger.info("Local index is complete.")
    elif diff > 0:
        logger.warning(f"Missing {diff} records.")
    else:
        logger.warning(f"Local index has {-diff} more records than fetched.")

    return diff


def get_last_processed_page(category_id: int) -> pd.DataFrame | None:
    """
    Retrieves the last successfully processed page and the table size at that time.

    Returns:
        pd.DataFrame: last entry found for category_id or None
    """

    if not INDEX_PROGRESS.exists():
        logger.info("Progress file not found")
        return

    try:
        df = pd.read_csv(INDEX_PROGRESS)
        df_cat = df[df["category_id"] == category_id]

        if not df_cat.empty:
            last_entry = df_cat.iloc[-1]
            logger.info(
                f"Resuming Category {category_id} from page {last_entry['current_page']} of {last_entry['saved_size']}"
            )
            return last_entry
        else:
            logger.info(f"No history found for Category {category_id}.")
    except Exception as e:
        logger.error(f"Error reading progress file: {e}")


def goto_last_processed_page(driver: WebDriver, target_page: int) -> None:
    """
    Navigates to the target_page using a sliding window strategy.
    Optimizes the path by choosing to start from the beginning or the end.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        target_page (int): The page number to reach.
    """
    try:
        last_page_elem = driver.find_element(By.XPATH, XPATH_LAST_PAGE)
        total_pages = int(last_page_elem.text.strip())

        logger.info(f"Navigating to processed page {target_page} (Total: {total_pages})...")

        if target_page > (total_pages / 2):
            logger.debug("Target is closer to the end. Jumping to Last Page.")
            last_page_elem.click()
            WebDriverWait(driver, 10).until(
                lambda d: int(d.find_element(By.XPATH, XPATH_CURRENT_PAGE).text) == total_pages
            )

        while True:
            current_elem = driver.find_element(By.XPATH, XPATH_CURRENT_PAGE)
            current_page = int(current_elem.text.strip())

            if current_page == target_page:
                logger.info(f"Arrived at target page {current_page}.")
                break

            pagination = driver.find_element(By.XPATH, XPATH_PAGINATION)
            links = pagination.find_elements(By.TAG_NAME, "a")

            visible_pages = {}
            for link in links:
                txt = link.text.strip()
                if txt.isdigit():
                    visible_pages[int(txt)] = link

            if not visible_pages:
                logger.error("Navigation stalled: No numeric pages visible.")
                break

            if target_page in visible_pages:
                visible_pages[target_page].click()
                next_expected = target_page
            elif current_page < target_page:
                next_expected = max(visible_pages.keys())
                visible_pages[next_expected].click()
            else:
                next_expected = min(visible_pages.keys())
                visible_pages[next_expected].click()

            WebDriverWait(driver, 10).until(
                lambda d: int(d.find_element(By.XPATH, XPATH_CURRENT_PAGE).text) == next_expected
            )

    except Exception as e:
        logger.error(f"Failed to navigate to last processed page: {e}")
        raise


# ====== Scraper Core Business Logic (Process) ======


def scrap_pages(driver: WebDriver, category_id: int, force: bool = False) -> None:
    """
    Iterates through all pages of a specific regulatory category, extracting and saving data.

    This function handles pagination navigation, saves checkpoints for every page found,
    and logs the execution progress. It supports resuming execution from the last
    checkpoint if 'force' is False and the table structure remains consistent.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The ID of the regulatory category to scrape.
        force (bool): If True, ignores previous progress, deletes existing chunks
                      for this category, and starts scraping from page 1.
                      Defaults to False.

    """
    search_size = 0
    url = CATEGORIES_URL % str(category_id)

    logger.info(f"Accessing ANVISA search page: {url}")
    driver.get(url)

    current_table_size_pages = set_max_table_size(driver)

    if force:
        delete_chunks(category_id)
    else:
        last_processed = get_last_processed_page(category_id)

        if last_processed["current_page"] == last_processed["last_page"]:
            logger.info(f"Category {category_id} processing already complete.")
            return

        elif last_processed["saved_size"] != current_table_size_pages:
            logger.warning(
                f"Table size inconsistent,{last_processed['saved_size']} != {current_table_size_pages}"
            )
            delete_chunks(category_id)
        else:
            goto_last_processed_page(driver, last_processed["current_page"])
            _, next_button, _ = get_pages(driver)
            next_button.click()

    # == scraping pages == #

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

        if pages["current"] >= pages["last"]:
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


def scrap_unit_category(category_id: int, force: bool = False) -> None:
    """
    Orchestrates the scraping process for a single regulatory category.

    This function acts as an isolated worker that:
    1. Validates the category against fetched metadata (skipping if empty or missing).
    2. Manages the lifecycle of a dedicated Selenium WebDriver instance.
    3. Delegates the actual extraction logic to `scrap_pages`.
    4. Encapsulates error handling to ensure thread safety and fault tolerance.

    Args:
        category_id (int): The unique identifier of the regulatory category.
        force (bool): If True, forces a fresh scrape ignoring previous progress.
                      Defaults to False.
    """
    logger.info(f"--- Starting Process for Category {category_id} ---")

    if metadata := get_fetch(category_id):
        expected = metadata["num_items"].sum()
        logger.info(f"Category {category_id}: Expecting {expected} items.")
    else:
        logger.warning(f"Skipping Category {category_id}: Metadata not found or empty.")
        return

    options = get_firefox_options()

    try:
        with webdriver_manager(options) as driver:
            scrap_pages(driver, category_id, force)
    except Exception as e:
        logger.exception(f"Process failed for Category {category_id}: {e}")


# ====== Fetch Core Business Logic (Process) ======


def fetch_unit_category(driver: WebDriver, category_id: int) -> list:
    """
    Navigates to the first and last page of a category to estimate data volume.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The regulatory category ID.

    Returns:
        list: ["category_id", "page_size", "last_page", "num_items"].
    """
    try:
        url = CATEGORIES_URL % str(category_id)
        logger.info(f"Fetching metadata for Category {category_id} | URL: {url}")

        driver.get(url)

        max_table_size = set_max_table_size(driver)
        pages, _, last_button = get_pages(driver)

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
            f"Fetched Category {category_id}: {total_items} items ({pages['last']} pages, {page_size} per page)"
        )

        return [
            category_id,
            max_table_size,
            pages["last"],
            total_items,
        ]
    except Exception:
        logger.warning(f"Category {category_id} seems empty or failed to load pagination.")
        return [category_id, 0, 0, 0]


# ====== Orchestration (Execution) ======


def scrap_categories(n_threads: int = 1, force: bool = False) -> None:
    """
    Orchestrates the parallel scraping of all categories.

    Manages the lifecycle of the scraping process:
    1. Prepares the environment (cleans chunks if force=True).
    2. Distributes scraping tasks across a thread pool.
    3. Consolidates results into a single file.

    Args:
        n_threads (int): Number of concurrent threads to use. Defaults to 1.
        force (bool): If True, deletes all previous chunks and starts fresh.
                      If False, attempts to resume based on progress.
    """
    logger.info(f"--- Starting Scraping Pipeline (Threads: {n_threads}, Force: {force}) ---")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    if force:
        logger.info("Force=True: Cleaning ALL temporary chunks before starting.")
        delete_chunks(category_id=None)

    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.map(
            partial(
                scrap_unit_category,
                force=force,
            ),
            CATEGORIES,
        )

    logger.info("Thread pool execution finished. Consolidating data chunks...")

    join_chunks(force)

    logger.info("Scraping Pipeline Finished")


def fetch_categories() -> None:
    """
    Orchestrates metadata fetching for all categories listed in CATEGORIES.

    Generates a CSV file (INDEX_FETCHED) containing the number of items and pages
    for each category, which serves as the baseline for validation.
    """
    logger.info("--- Setup Fetch Execution ---")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    options = get_firefox_options()
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
                fetch_values.append([category_id, 0, 0, 0])

        fetch_df = pd.DataFrame(fetch_values, columns=FETCH_COLUMNS)
        fetch_df.to_csv(INDEX_FETCHED, index=False)

        logger.info(f"Fetch complete. Metadata saved to {INDEX_FETCHED}")

    except Exception as e:
        logger.critical(f"Critical error during categories fetch: {e}")
        raise


# ====== SCRIPT ENTRY POINT ======

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
            help="Number of threads for parallel processing.",
            min=1,
            max=len(CATEGORIES),
            show_default=True,
        ),
    ] = 1,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force execution to start from zero (Ignores resume).",
            show_default=False,
        ),
    ] = False,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            "-c",
            help="Only check execution status (Local Index vs Remote Metadata).",
            show_default=False,
        ),
    ] = False,
    update: Annotated[
        bool,
        typer.Option(
            "--update/--no-update",
            "-u/-U",
            help="Fetch fresh metadata from ANVISA before starting.",
            show_default=True,
        ),
    ] = True,
) -> None:
    """
    Runs the ANVISA drug listing scraper pipeline.
    """
    try:
        # 1. Update Metadata (if requested or default)
        if update:
            fetch_categories()

        # 2. Check Mode (Exit after check)
        if check:
            check_index()
            return

        # 3. Standard Pipeline Execution
        logger.info(f"Starting pipeline (Threads: {n_threads}, Force: {force})...")

        scrap_categories(n_threads=n_threads, force=force)

        logger.info(f"Pipeline execution complete. Log: {log_file_path.resolve()}")

    except Exception as e:
        logger.exception(f"Fatal error during pipeline execution: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    from drugslm.utils.logging import get_log_path, setup_logging

    log_file_path = get_log_path(__file__)
    setup_logging(log_file_path)

    app()
