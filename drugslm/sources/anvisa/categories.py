"""ANVISA Drug Categories Scraper.

This module is responsible for the extraction of drug listing data from ANVISA's
search interface, categorized by regulatory definitions. It navigates through
pagination, extracts tabular data, and consolidates it for downstream processing.

Scope:
    This module is responsible for:
    - Iterating through specific regulatory categories (IDs 1-12).
    - Handling Selenium pagination and table parsing.
    - Persisting raw chunks of data to avoid data loss during long runs.
    - Consolidating chunks into a final Pickle/CSV dataset.
    - Checking consistency between fetched metadata and scraped data.

    This module is not responsible for:
    - Downloading PDFs or leaflets (handled by a separate downloader module).
    - Parsing the content of the leaflets.
    - Interacting with the "DADOS_ABERTOS_MEDICAMENTOS.csv" metadata file.

Execution Flow:
    1.  **Scan (`crawl`)**: : Initializes the category-based search list scan by checking the first and last page.
    2.  **Orchestration (`scrape`)**: Initializes thread pool and manages directory setup.
    3.  **Unit Execution (`scrape_unit`)**: Instantiates a WebDriver for a specific category.
    4.  **Navigation (`scrape_pages`)**: Accesses the category URL and iterates through pages.
    5.  **Extraction (`table2data`)**: Parses HTML tables into structured lists.
    6.  **Persistence (`save_chunk`)**: Saves intermediate data (chunks) to disk.
    7.  **Consolidation (`join_chunks`)**: Merges all chunks into a single dataset.

Data Persistence:
    - **Chunks**: Temporary `.pkl` files saved per page in `data/raw/anvisa/categories/chunks/`.
    - **Progress**: `progress.csv` tracks the last successfully saved page per category.
    - **Final Output**: `categories.pkl` and `categories.csv` containing the consolidated dataframe.
    - **Metadata**: `crawled.csv` containing the expected number of items per category.

Prerequisites:
    - Selenium Grid (Hub) running and accessible via `HUB_URL`.
    - Firefox/Chrome nodes connected to the Hub.

Known Limitations:
    - Dependent on specific XPath structures (`XPATH_PAGINATION`, `XPATH_PAGE_COUNT`).
      UI changes on the ANVISA portal may break the scraper.
    - The "Items per page" selector is fragile and may fail if the DOM loads slowly.

Authors:
    - Vinícius de Lima Gonçalves
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
import logging
from pathlib import Path
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

from drugslm.sources.anvisa import ANVISA_DIR, ANVISA_URL
from drugslm.utils.asserts import assert_text_number
from drugslm.utils.selenium import highlight, scroll, webdriver_manager

logger = logging.getLogger(__name__)

# ====== RUNTIME CONSTANTS ======

SLEEPSECS = 1
"""int: Time in seconds to wait between page transitions to avoid rate limiting."""

WAITSECS = 5
"""int: Maximum time in seconds to wait for an element to appear (Explicit Wait)."""

# ====== CATEGORIES CONSTANTS =====

CATEGORIES_ID = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
"""list[int]: List of regulatory category IDs to be scraped from the ANVISA portal."""

CATEGORIES_URL = ANVISA_URL + "?categoriasRegulatorias=%s"
"""str: Template URL for the search page, expecting a category ID as a parameter."""

# ====== DIRS and OUTPUTS ======

CATEGORIES_DIR = ANVISA_DIR / "categories"
"""Path: Main directory for storing category-related data."""

CRAWL_FILE = CATEGORIES_DIR / "crawled.csv"
"""Path: File storing metadata (count/pages) fetched from the portal for validation."""

PROGRESS_FILE = CATEGORIES_DIR / "progress.csv"
"""Path: File tracking the scraping progress to allow resuming execution."""

CHUNKS_DIR = CATEGORIES_DIR / "chunks"
"""Path: Directory for temporary pickle files containing page-level data."""

CATEGORIES_FILE = CATEGORIES_DIR / "categories.pkl"
"""Path: Final consolidated output file containing all scraped data."""

# ====== XPATH FOR HTML ELEMENTS =====

XPATH_PAGINATION = "//ul[contains(@class, 'pagination')]"
"""str: XPath to locate the pagination container."""

XPATH_CURRENT_PAGE = f"{XPATH_PAGINATION}//li[contains(@class, 'active')]//a"
"""str: XPath to locate the currently active page number."""

XPATH_LAST_PAGE = f"{XPATH_PAGINATION}//a[contains(@ng-switch-when, 'last')]"
"""str: XPath to locate the 'Last' button in pagination."""

XPATH_PAGE_COUNT = "//div[contains(@class, 'ng-table-counts')]"
"""str: XPath to locate the 'items per page' dropdown/buttons container."""

# ====== COLUMNS =====

CATEGORIES_COLUMNS = [
    "id",
    "page",
    "drug",
    "link",
    "company",
    "protocol",
    "pub_date",
]
"""list[str]: Column names for the final scraped dataset."""

METADATA_COLUMNS = [
    "id",
    "items_page",
    "last_page",
    "size",
]
"""list[str]: Column names for the metadata (crawled) file."""

# ====== Helpers (Primitives) ======


def sel_max_items_page(driver: WebDriver) -> int:
    """Attempts to select the highest available "items per page" option (e.g., 50).

    Iterates through options in reverse order (highest to lowest). If the highest
    option fails, it tries the next lower one. Exceptions are swallowed to prevent
    script execution stoppage, defaulting to 0 if unsuccessful.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Returns:
        int: The selected items per page value. Returns 0 if failed.
    """
    try:
        container = WebDriverWait(driver, WAITSECS).until(
            EC.presence_of_element_located((By.XPATH, XPATH_PAGE_COUNT))
        )

        buttons = container.find_elements(By.TAG_NAME, "button")

        if not buttons:
            logger.warning(
                "Pagination count container found, but no buttons were visible. Returning 0."
            )
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
                    f"Failed to click page count option '{btn.text}'. Trying previous. Error: {str(e).splitlines()[0]}"
                )
                continue

        logger.error("Exited the loop with nothing. Returning 0.")
        return 0

    except Exception as e:
        logger.warning(
            f"Element for items per page not found: {str(e).splitlines()[0]}. Returning 0."
        )
        return 0


def table2data(element: WebElement) -> list:
    """Parses the HTML table element and extracts rows into a list of data.

    Uses BeautifulSoup for efficient parsing of the inner HTML of the WebElement.

    Args:
        element (WebElement): The Selenium WebElement containing the `<table>`.

    Returns:
        list: A list of lists, where each inner list represents a row:
              [drug, link, company, protocol, pub_date].
              Returns empty list [] on failure.
    """
    try:
        logger.info("Starting table HTML parsing...")

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

            drug_cell = tds[0]
            drug = drug_cell.get_text(strip=True) or None

            a_tag = drug_cell.find("a")
            link_drug = a_tag["href"] if a_tag and a_tag.has_attr("href") else None

            company = tds[1].get_text(strip=True) or None
            protocol = tds[2].get_text(strip=True) or None
            pub_date = tds[3].get_text(strip=True) or None

            row = [drug, link_drug, company, protocol, pub_date]
            data.append(row)

        logger.info(f"Table parsed successfully. Extracted {len(data)} rows.")
        return data

    except Exception as e:
        logger.exception(f"Unexpected error while parsing table data: {str(e).splitlines()[0]}")
        return []


def get_pages(driver: WebDriver) -> Tuple[dict, WebElement | None, WebElement | None]:
    """Captures the current state of pagination controls and the next page element.

    Retries on failure (e.g., StaleElementReferenceException, TimeoutException).

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Returns:
        Tuple[dict, WebElement, WebElement]: A tuple containing:
            - dict: A dictionary with keys 'current', 'next', and 'last' (all integers).
            - WebElement: The Selenium element corresponding to the *next* page button (or None).
            - WebElement: The Selenium element corresponding to the *last* page button (or None).

    Raises:
        TimeoutException: If the pagination container is not found (caught internally, returns default).
    """
    try:
        pagination = WebDriverWait(driver, WAITSECS).until(
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
        logger.warning(
            f"Pagination not found ({str(e).splitlines()[0]}). Defaulting to Single Page view."
        )
        return (
            {
                "current": 1,
                "next": 1,
                "last": 1,
            },
            None,
            None,
        )


def resolve_next_page(current_page: WebElement, last_page: WebElement) -> Tuple[int, int, int]:
    """Parses pagination WebElements to extract page numbers and calculate the next target.

    Validates that the text content of the elements is numeric before converting.
    Logic ensures `next_page` does not exceed `last_page`.

    Args:
        current_page (WebElement): The WebElement representing the currently active page.
        last_page (WebElement): The WebElement representing the last available page.

    Returns:
        Tuple[int, int, int]: (current_page_num, last_page_num, next_page_num).

    Raises:
        AssertionError: If element text is not numeric.
        ValueError: If conversion to integer fails.
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


@retry(tries=2, delay=2, backoff=2, logger=None)
def find_table(driver: WebDriver) -> WebElement:
    """Waits for the main results table to be present in the DOM.

    Uses visual helpers (scroll and highlight) to assist debugging and visibility.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.

    Returns:
        WebElement: The found `<table>` element.

    Raises:
        TimeoutException: If the table is not found within the timeout period (after retries).
    """
    try:
        logger.info("Attempting to find table element...")

        table = WebDriverWait(driver, WAITSECS).until(
            EC.presence_of_element_located((By.TAG_NAME, "table")),
        )

        scroll(driver, table)
        highlight(driver, table, color="blue")

        logger.info("Table found successfully.")
        return table

    except Exception as e:
        logger.error("Failed to find table after retries.")
        logger.warning(f"Table not found: {str(e).splitlines()[0]}. Retrying...")
        raise


# ====== I/O & Persistence (File Handling) ======


def rotate_file(filepath: Path) -> None:
    """Renames a file by appending a timestamp, acting as a backup rotation.

    Example: `data.csv` -> `data_20231027103000.csv`

    Args:
        filepath (Path): Path object to the file to be rotated.
    """
    if not filepath.exists():
        return

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Constrói novo nome: stem (nome sem ext) + timestamp + suffix (extensão)
    new_name = f"{filepath.stem}_{timestamp}{filepath.suffix}"
    new_path = filepath.with_name(new_name)

    try:
        filepath.rename(new_path)
        logger.info(f"Rotated/Archived file: {filepath.name} -> {new_name}")
    except Exception as e:
        logger.warning(f"Failed to rotate file {filepath}: {e}")


def save_chunk(raw_data: list[list], category_id: int, page_num: int) -> int:
    """Saves a single page of scraped data to a pickle file (chunk).

    Adds metadata columns (category_id, page_num) to the raw data before saving.

    Args:
        raw_data (list): The raw data list extracted from the table.
        category_id (int): The category ID being processed.
        page_num (int): The current page number.

    Returns:
        int: The number of rows saved.
    """
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = CHUNKS_DIR / f"{category_id}_{page_num}.pkl"

    full_data = [[category_id, page_num] + row for row in raw_data]

    df = pd.DataFrame(data=full_data, columns=CATEGORIES_COLUMNS)
    df.to_pickle(output_path)

    logger.info(f"Table checkpoint saved: {output_path}")
    return len(df)


def join_chunks(force: bool = False) -> None:
    """Consolidates all individual page pickle files into a single DataFrame.

    It can either overwrite the existing final file or merge new chunks with
    the existing data, handling deduplication based on 'protocol'.

    Args:
        force (bool): If True, completely overwrites the existing categories file.
                      If False, merges new chunks with existing data based on protocol number.
    """

    all_files = list(CHUNKS_DIR.glob("*.pkl"))

    if not all_files:
        logger.warning(f"No pickle files found to consolidate in {CHUNKS_DIR}.")
        return

    logger.info(f"{len(all_files)} chunks found. Starting consolidation...")

    try:
        new_data = pd.concat([pd.read_pickle(f) for f in all_files], ignore_index=True)

        if force or not CATEGORIES_FILE.exists():
            logger.info("Overwriting final table.")
            final_df = new_data
        else:
            logger.info("Merging new chunks with existing categories.")
            try:
                old_data = pd.read_pickle(CATEGORIES_FILE)

                combined = pd.concat([old_data, new_data])

                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                combined.loc[
                    combined.duplicated(
                        ["protocol"],
                        keep=False,
                    )
                ].to_pickle(CATEGORIES_DIR / f"duplicates_to_debug_{timestamp}.pkl")

                logger.info("Deduplicating based on 'protocol' keeping last")
                final_df = combined.drop_duplicates(
                    subset=["protocol"],
                    keep="last",
                )

            except Exception as e:
                logger.error(
                    f"Failed to merge with existing table, falling back to overwrite: {str(e).splitlines()[0]}"
                )
                final_df = new_data

        # Save Final Result
        final_df.to_pickle(CATEGORIES_FILE)
        final_df.to_csv(CATEGORIES_FILE.with_suffix(".csv"), index=False)

        logger.info(f"Consolidation complete. Saved {len(final_df)} rows to {CATEGORIES_FILE}")

        # Only delete chunks if consolidation was successful
        delete_chunks()

    except Exception as e:
        logger.error(f"Critical error during join_chunks: {str(e).splitlines()[0]}")


def delete_lock_progress() -> None:
    """Removes stale lock files from previous executions to prevent deadlocks.

    This should be called only during single-threaded orchestration (start of pipeline).
    """
    lock_file = PROGRESS_FILE.with_suffix(".csv.lock")
    if lock_file.exists():
        try:
            lock_file.unlink()
            logger.info("Removed stale lock file from previous run.")
        except Exception as e:
            logger.warning(f"Could not remove stale lock file: {e}")


def delete_chunks(category_id: int | None = None) -> None:
    """Deletes temporary chunk files from the chunk directory.

    Args:
        category_id (int | None): If provided, deletes only chunks for that category.
                                  If None, deletes all chunks in the directory.
    """
    # 1. Limpeza de Chunks
    pattern = f"{category_id}_*.pkl" if category_id else "*.pkl"
    all_files = list(CHUNKS_DIR.glob(pattern))

    if all_files:
        try:
            for f in all_files:
                f.unlink()
            logger.info(f"Deleted {len(all_files)} chunk files.")
        except Exception as e:
            logger.error(f"Error deleting chunk files: {str(e).splitlines()[0]}")
    else:
        logger.info(f"No chunks found to delete for pattern: {pattern}")

    if category_id is None and CHUNKS_DIR.exists() and not any(CHUNKS_DIR.iterdir()):
        try:
            CHUNKS_DIR.rmdir()
        except Exception:
            pass


def save_progress(category_id: int, pages: dict, saved_size: int) -> None:
    """Appends execution progress to a CSV file with file locking.

    This ensures that multiple threads do not corrupt the progress file.

    Args:
        category_id (int): The category ID being processed.
        pages (dict): Pagination state dictionary {'current', 'next', 'last'}.
        saved_size (int): Number of rows saved in this step.
    """
    lock_path = PROGRESS_FILE.with_suffix(".csv.lock")

    with FileLock(lock_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        with open(PROGRESS_FILE, "a") as out:
            if not PROGRESS_FILE.exists() or PROGRESS_FILE.stat().st_size == 0:
                out.write("timestamp,category_id,current_page,last_page,saved_size\n")

            out.write(
                f"{timestamp},{category_id},{pages['current']},{pages['last']},{saved_size}\n"
            )


def get_categories() -> pd.DataFrame | None:
    """Loads the final consolidated categories DataFrame.

    Returns:
        pd.DataFrame: Consolidated categories DataFrame.
        None: If the file is missing or empty.
    """
    try:
        df = pd.read_pickle(CATEGORIES_FILE)
        if not df.empty:
            return df

    except FileNotFoundError:
        logger.warning(f"Index table {CATEGORIES_FILE} not found. Returning None.")
    except Exception as e:
        logger.error(f"Error reading categories table: {str(e).splitlines()[0]}")


def get_crawled(category_id: int | None = None) -> pd.DataFrame | None:
    """Loads the crawled metadata file.

    Can return the entire DataFrame or filter for a specific category size.

    Args:
        category_id (int | None): Optional ID to filter specific size.

    Returns:
        pd.DataFrame: All metadata or specific row if category_id passed.
        None: If not found or error.
    """

    if not CRAWL_FILE.exists():
        logger.warning(f"Fetch file not found at {CRAWL_FILE}. Returning None.")
        return None

    try:
        df = pd.read_csv(CRAWL_FILE)

        if category_id is None:
            logger.info(f"Loaded crawled categories metadata ({len(df)} records).")
            return df if not df.empty else None

        row = df.loc[df["id"] == category_id]

        if row.empty:
            logger.warning(f"Category {category_id} not found in metadata file.")
            return None

        return row

    except Exception as e:
        logger.error(
            f"Error reading metadata file categories {category_id} : {str(e).splitlines()[0]}"
        )
        return None


def check_categories(category_id: int | None = None) -> int:
    """Checks the consistency between the local categories and the ANVISA database.

    Compares the row count of the local consolidated file against the
    metadata fetched from the live site (crawled file).

    Args:
        category_id (int | None): ID to check specific category consistency.
                                  If None, checks global consistency.

    Returns:
        int: The difference between expected and found records (expected - found).
    """
    logger.info(
        f"--- Starting Index Check (Target: {category_id if category_id else 'Global'}) ---"
    )

    if (df_local := get_categories()) is None:
        logger.error("Could not obtain local categories for comparison.")
        return -1

    if category_id:
        df_local = df_local[df_local["id"] == category_id]

    local_size = len(df_local)
    logger.info(f"Local categories found: {local_size} records.")

    if (crawled_df := get_crawled(category_id)) is None:
        logger.error("Could not obtain metadata for comparison.")
        return -1

    expected_size = crawled_df["size"].sum()
    diff = expected_size - local_size

    logger.info("--- Index Consistency Report ---")
    logger.info(f"Expected (Remote) : {expected_size:>8}")
    logger.info(f"Found    (Local)  : {local_size:>8}")
    logger.info(f"Difference        : {diff:>8}")
    logger.info("-" * 34)

    if diff == 0:
        logger.info("Local categories is complete.")
    elif diff > 0:
        logger.warning(f"Missing {diff} records.")
    else:
        logger.warning(f"Local categories has {-diff} more records than fetched.")

    return diff


def get_last_processed_page(category_id: int) -> pd.DataFrame | None:
    """Retrieves the last successfully processed page and the table size at that time.

    Used to resume execution from a specific point.

    Args:
        category_id (int): The category ID to check.

    Returns:
        pd.DataFrame: The last progress entry found for category_id, or None.
    """

    if not PROGRESS_FILE.exists():
        logger.info("Progress file not found")
        return

    try:
        df = pd.read_csv(PROGRESS_FILE)
        df_cat = df[df["id"] == category_id]

        if not df_cat.empty:
            last_entry = df_cat.iloc[-1]
            logger.info(
                f"Resuming Category {category_id} from page {last_entry['current_page']} of {last_entry['saved_size']}"
            )
            return last_entry
        else:
            logger.info(f"No history found for Category {category_id}.")
    except Exception as e:
        logger.error(f"Error reading progress file: {str(e).splitlines()[0]}")


def goto_last_processed_page(driver: WebDriver, target_page: int) -> None:
    """Navigates directly to the target_page using a sliding window strategy.

    Optimizes the path by choosing to start from the beginning or the end (Last Page),
    then iterating through the visible pagination window until the target is found.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        target_page (int): The page number to reach.

    Raises:
        Exception: If navigation fails.
    """
    try:
        last_page_elem = driver.find_element(By.XPATH, XPATH_LAST_PAGE)
        total_pages = int(last_page_elem.text.strip())

        logger.info(f"Navigating to processed page {target_page} (Total: {total_pages})...")

        if target_page > (total_pages / 2):
            logger.info("Target is closer to the end. Jumping to Last Page.")
            last_page_elem.click()
            WebDriverWait(driver, WAITSECS).until(
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

            WebDriverWait(driver, WAITSECS).until(
                lambda d: int(d.find_element(By.XPATH, XPATH_CURRENT_PAGE).text) == next_expected
            )

    except Exception as e:
        logger.error(f"Failed to navigate to last processed page: {str(e).splitlines()[0]}")
        raise


# ====== Scraper Core Business Logic (Process) ======


def scrape_pages(driver: WebDriver, category_id: int, force: bool = False) -> None:
    """Iterates through all pages of a specific regulatory category.

    Extracts table data, saves checkpoints, and handles pagination.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The ID of the regulatory category to scrape.
        force (bool): If True, ignores previous progress and starts from page 1.
                      Defaults to False.
    """
    search_size = 0
    url = CATEGORIES_URL % str(category_id)

    logger.info(f"Accessing ANVISA search page: {url}")
    driver.get(url)

    items_page = sel_max_items_page(driver)

    if force:
        logger.info(f"Clearing previous chunks for Category {category_id} to start fresh.")
        delete_chunks(category_id)
    elif (last_processed := get_last_processed_page(category_id)) is not None:
        if last_processed["current_page"] == last_processed["last_page"]:
            logger.info(f"Category {category_id} was fully processed in previous run. Skipping.")
            return

        elif last_processed["saved_size"] != items_page:
            logger.warning(
                f"Table size inconsistent,{last_processed['saved_size']} != {items_page}. Structure changed. Restarting category."
            )
            delete_chunks(category_id)
        else:
            target_page = int(last_processed["current_page"])
            logger.info(f"Resuming Category {category_id} from Page {target_page}...")

            goto_last_processed_page(driver, target_page)
            sleep(SLEEPSECS)

            _, next_button, _ = get_pages(driver)

            if next_button:
                logger.info("Clicking Next to continue scraping...")
                next_button.click()
            else:
                logger.error(
                    "Resume pointed to a page with no 'Next' button. Scraping current page again."
                )
    else:
        logger.info(f"No progress found for Category {category_id}. Starting fresh.")
        delete_chunks(category_id)

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

        saved_size = save_chunk(data, category_id, pages["current"])
        save_progress(category_id, pages, saved_size)
        search_size += saved_size

        if (pages["current"] >= pages["last"]) or (next_button is None):
            logger.info("Last page reached. Ending scrape.")
            break

        previous_page = pages["current"]

        scroll(driver, next_button)
        highlight(driver, next_button, color="green")

        next_button.click()
        sleep(SLEEPSECS)

        pages, next_button, _ = get_pages(driver)
        sleep(SLEEPSECS)

        if previous_page == pages["current"]:
            logger.warning(
                f"Page did not change after click: {pages['current']} == {previous_page}. Stopping to avoid loop."
            )
            break

    logger.info(f"Category {category_id} processing complete. Total rows saved: {search_size}")


def scrape_unit(category_id: int, force: bool = False) -> None:
    """Orchestrates the scraping process for a single regulatory category.

    This function acts as an isolated worker that:
    1. Validates the category against crawled metadata.
    2. Manages the lifecycle of a dedicated Selenium WebDriver instance.
    3. Delegates the actual extraction logic to `scrape_pages`.

    Args:
        category_id (int): The unique identifier of the regulatory category.
        force (bool): If True, forces a fresh scrape ignoring previous progress.
    """
    try:
        logger.info(f"--- Starting Process for Category {category_id} ---")

        if (crawled_df := get_crawled(category_id)) is not None:
            expected = int(crawled_df["size"].sum())
            logger.info(f"Category {category_id}: Expecting {expected} items.")
        else:
            logger.warning(f"Skipping Category {category_id}: Metadata not found or empty.")
            return

        with webdriver_manager() as driver:
            scrape_pages(driver, category_id, force)

    except Exception as e:
        logger.exception(f"Process failed for Category {category_id}: {str(e).splitlines()[0]}")


# ====== Fetch Core Business Logic (Process) ======


def crawl_unit(driver: WebDriver, category_id: int) -> list:
    """Navigates to the first and last page of a category to estimate data volume.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The regulatory category ID.

    Returns:
        list: A list containing ["id", "page_size", "last_page", "size"].
    """
    try:
        url = CATEGORIES_URL % str(category_id)
        logger.info(f"Crawling metadata for Category {category_id} | URL: {url}")

        driver.get(url)

        items_page = sel_max_items_page(driver)
        sleep(SLEEPSECS)

        pages, _, last_button = get_pages(driver)

        table1 = find_table(driver)
        data1 = table2data(table1)
        page_size = len(data1)  # == items_page if not unique page

        if pages["last"] > 1:
            logger.info(f"Category {category_id}: Jumping to last page ({pages['last']})...")
            last_button.click()
            sleep(SLEEPSECS)

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
            items_page,
            pages["last"],
            total_items,
        ]
    except Exception:
        logger.warning(f"Category {category_id} seems empty or failed to load pagination.")
        return [category_id, 0, 0, 0]


# ====== Orchestration (Execution) ======


def scrape(n_threads: int = 1, force: bool = False) -> None:
    """Orchestrates the parallel scraping of all categories.

    Manages the lifecycle of the scraping process:
    1. Prepares the environment (creates dirs, cleans chunks if force=True).
    2. Distributes scraping tasks across a thread pool.
    3. Consolidates results into a single file.

    Args:
        n_threads (int): Number of concurrent threads to use. Defaults to 1.
        force (bool): If True, deletes all previous chunks and starts fresh.
    """
    logger.info(f"--- Starting Scraping Pipeline (Threads: {n_threads}, Force: {force}) ---")

    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)
    delete_lock_progress()

    if force:
        logger.info("Force=True: Cleaning ALL temporary chunks before starting.")
        delete_chunks(category_id=None)

        logger.info("Performing global cleanup: Rotating main artifacts.")

        rotate_file(PROGRESS_FILE)
        rotate_file(CATEGORIES_FILE)

    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        list(
            executor.map(
                partial(
                    scrape_unit,
                    force=force,
                ),
                CATEGORIES_ID,
            )
        )

    logger.info("Thread pool execution finished. Consolidating data chunks...")

    join_chunks(force)

    logger.info("Scraping Pipeline Finished")


def crawl() -> None:
    """Orchestrates metadata fetching for all categories listed in CATEGORIES_ID.

    Generates a CSV file (CRAWL_FILE) containing the number of items and pages
    for each category, which serves as the baseline for validation.
    """
    logger.info("--- Setup Fetch Execution ---")
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)
    rotate_file(CRAWL_FILE)

    fetch_values = []

    logger.info("--- Starting Fetch Routine for All Categories ---")

    try:
        for category_id in CATEGORIES_ID:
            try:
                with webdriver_manager() as driver:
                    stats = crawl_unit(driver, category_id)
                    fetch_values.append(stats)
            except Exception as e:
                logger.error(
                    f"Failed to fetch metadata for Category {category_id}: {str(e).splitlines()[0]}"
                )
                fetch_values.append([category_id, 0, 0, 0])

        fetch_df = pd.DataFrame(fetch_values, columns=METADATA_COLUMNS)
        fetch_df.to_csv(CRAWL_FILE, index=False)

        logger.info(f"Fetch complete. Metadata saved to {CRAWL_FILE}")

    except Exception as e:
        logger.critical(f"Critical error during categories fetch: {str(e).splitlines()[0]}")
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
            max=len(CATEGORIES_ID),
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
            help="Only check execution status (Local Crawled vs Remote Metadata).",
            show_default=False,
        ),
    ] = False,
    crawl_only: Annotated[
        bool,
        typer.Option(
            "--crawl-only",
            "--crawl",
            help="Only crawl fresh metadata from ANVISA and exit.",
            show_default=False,
        ),
    ] = False,
    skip_crawl: Annotated[
        bool,
        typer.Option(
            "--no-crawl",
            "--skip-crawl",
            help="Skip crawling fresh metadata (uses existing file).",
            show_default=False,
        ),
    ] = False,
) -> None:
    """Runs the ANVISA drug listing scraper pipeline."""
    try:
        if check:
            check_categories()
            return

        if not skip_crawl:
            crawl()

        if crawl_only:
            return

        logger.info(f"Starting pipeline (Threads: {n_threads}, Force: {force})...")

        scrape(n_threads=n_threads, force=force)

        logger.info(f"Pipeline execution complete. Log: {log_file_path.resolve()}")

    except Exception as e:
        logger.exception(f"Fatal error during pipeline execution: {str(e).splitlines()[0]}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    from drugslm.utils.logging import get_log_path, setup_logging

    log_file_path = get_log_path(__file__)
    setup_logging(log_file_path)

    app()