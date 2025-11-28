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
Documentation: Gemini 3 Pro (Student), Vinícius de Lima Gonçalves
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
import logging
from time import sleep
from typing import Dict, List, Optional, Tuple

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
        list: A list of lists [medicamento, link, empresa, expediente, data_pub].
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
def get_pages(driver: WebDriver) -> Tuple[dict, WebElement, WebElement]:
    """
    Captures the current state of pagination controls and the next page element.

    Returns:
        Tuple:
            - dict: {'current', 'next', 'last'} (integers).
            - WebElement: The *next* page button.
            - WebElement: The *last* page button.
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
            f"Captured pagination. Current {current_page_number}, Last {last_page_number}."
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
    """
    try:
        logger.debug("Attempting to find table element...")

        table = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "table")),
        )

        scroll(driver, table)
        highlight(driver, table, color="blue")

        return table

    except Exception:
        logger.error("Failed to find table after retries.")
        raise


# ====== I/O & Persistence (File Handling) ======


def save_chuck(data: list[list], category_id: int, page_num: int) -> int:
    """
    Saves a single page of scraped data to a pickle file.
    """
    INDEX_CHUNKS.mkdir(parents=True, exist_ok=True)

    output_path = INDEX_CHUNKS / f"{category_id}_{page_num}.pkl"

    df = pd.DataFrame(data=data, columns=SEARCH_COLUMNS)
    df.insert(0, "id", value=category_id)
    df.insert(0, "page", value=page_num)
    df.to_pickle(output_path)

    logger.info(f"Table checkpoint saved: {output_path}")
    return len(df)


def join_chunks(force: bool = False) -> None:
    """
    Consolidates all individual page pickle files into a single DataFrame.
    If force=False, merges with existing data using 'expediente' as key.
    """
    all_files = list(INDEX_CHUNKS.glob("*.pkl"))

    if not all_files:
        logger.warning(f"No pickle files found to consolidate in {INDEX_CHUNKS}.")
        return

    logger.info(f"{len(all_files)} chunks found. Starting consolidation...")

    try:
        new_data = pd.concat([pd.read_pickle(f) for f in all_files], ignore_index=True)

        if force or not INDEX_TABLE.exists():
            logger.info("Force=True or no previous index: Overwriting final table.")
            final_df = new_data
        else:
            logger.info("Force=False: Merging new chunks with existing index.")
            try:
                old_data = pd.read_pickle(INDEX_TABLE)

                # Combine old and new
                combined = pd.concat([old_data, new_data])

                # Deduplicate logic
                # 'expediente' is generally unique for a specific drug transaction/doc.
                # If 'expediente' is not reliable, we fallback to 'link_medicamento' + 'medicamento'.
                # We keep 'last' to ensure the freshest data from chunks takes precedence.
                subset_cols = (
                    ["expediente"]
                    if "expediente" in combined.columns
                    else ["medicamento", "link_medicamento"]
                )

                logger.info(f"Deduplicating based on: {subset_cols}")
                final_df = combined.drop_duplicates(subset=subset_cols, keep="last")

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
    Appends execution metadata to a CSV file.
    """
    lock_path = INDEX_PROGRESS.with_suffix(".csv.lock")

    with FileLock(lock_path):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        with open(INDEX_PROGRESS, "a") as out:
            # Note: Header must match the write order below
            if not INDEX_PROGRESS.exists() or INDEX_PROGRESS.stat().st_size == 0:
                out.write("timestamp,category_id,current_page,last_page,saved_size\n")

            out.write(
                f"{timestamp},{category_id},{pages['current']},{pages['last']},{saved_size}\n"
            )


def get_index() -> pd.DataFrame:
    """
    Loads the final consolidated index. Returns empty DataFrame if not found.
    """
    try:
        return pd.read_pickle(INDEX_TABLE)
    except FileNotFoundError:
        logger.warning(f"Index table {INDEX_TABLE} not found. Returning empty DataFrame.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading index table: {e}")
        return pd.DataFrame()


def get_fetch(category_id: int | None = None) -> Dict | None:
    """
    Loads categories metadata.

    Args:
        category_id: ID to filter.

    Returns:
        Dict: {'id', 'pages', 'size'} for the specific category.
        DataFrame: If category_id is None (returns all).
        None: If file missing or ID not found.
    """
    if not INDEX_FETCHED.exists():
        logger.warning(f"Fetch file not found at {INDEX_FETCHED}. Returning None.")
        return None

    try:
        df = pd.read_csv(INDEX_FETCHED)

        if category_id is None:
            return df

        row = df.loc[df["id"] == category_id]
        if row.empty:
            logger.warning(f"Category {category_id} not found in fetch file.")
            return None

        # Convert the row series to a dict
        return row.iloc[0].to_dict()

    except Exception as e:
        logger.error(f"Error reading fetched categories CSV: {e}")
        return None


def check_index() -> int:
    """
    Checks consistency between local index and remote metadata.

    Returns:
        int: Difference (Expected - Found).
    """
    logger.info("--- Starting Index Check ---")

    df_local = get_index()
    local_size = len(df_local)
    logger.info(f"Local index found: {local_size} records.")

    logger.info("Loading stored metadata...")
    df_meta = get_fetch(category_id=None)  # Get all

    if df_meta is None or df_meta.empty:
        logger.error("Could not obtain metadata for comparison.")
        return -1

    expected_size = int(df_meta["total"].sum())

    diff = expected_size - local_size

    logger.info("=" * 40)
    logger.info(f"EXPECTED: {expected_size}")
    logger.info(f"FOUND:    {local_size}")
    logger.info("=" * 40)

    if diff == 0:
        logger.info("Local index is complete (Synced).")
    elif diff > 0:
        logger.warning(f"Missing {diff} records.")
    else:
        logger.warning(f"Local index has {-diff} more records than fetched (Surplus).")

    return diff


def get_last_processed_page(category_id: int) -> Tuple[int, int]:
    """
    Retrieves the last successfully processed page and the table size at that time.

    Returns:
        Tuple[int, int]: (last_processed_page, saved_last_page_count)
    """
    if not INDEX_PROGRESS.exists():
        return 0, 0

    try:
        df = pd.read_csv(INDEX_PROGRESS)
        # Filter for specific category
        df_cat = df[df["category_id"] == category_id]

        if df_cat.empty:
            return 0, 0

        # Get the last entry
        last_entry = df_cat.iloc[-1]
        return int(last_entry["current_page"]), int(last_entry["last_page"])

    except Exception as e:
        logger.error(f"Error reading progress file: {e}")
        return 0, 0


def goto_last_processed_page(driver: WebDriver, target_page: int) -> None:
    """
    Navigates to the target_page using a sliding window strategy.
    """
    try:
        last_page_elem = driver.find_element(By.XPATH, XPATH_LAST_PAGE)
        total_pages = int(last_page_elem.text.strip())

        logger.info(f"Navigating to processed page {target_page} (Total: {total_pages})...")

        # Jump to end if closer
        if target_page > (total_pages / 2):
            logger.debug("Target is closer to the end. Jumping to Last Page.")
            last_page_elem.click()
            WebDriverWait(driver, 10).until(
                lambda d: int(d.find_element(By.XPATH, XPATH_CURRENT_PAGE).text) == total_pages
            )

        # Sliding Window
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
    Iterates through pages, extracting and saving data. Handles Resume vs Force logic.
    """
    search_size = 0
    url = CATEGORIES_URL % str(category_id)

    logger.info(f"Accessing ANVISA search page: {url}")
    driver.get(url)

    current_table_size_pages = set_max_table_size(driver)

    # --- Resume Logic ---
    start_from_scratch = force

    if not force:
        last_processed_page, saved_total_pages = get_last_processed_page(category_id)

        # Check if we have progress and if the site structure hasn't changed
        if last_processed_page > 0 and saved_total_pages == current_table_size_pages:
            try:
                goto_last_processed_page(driver, last_processed_page)

                # Navigate to the NEXT page to continue scraping
                # (We re-scrape the last processed one just in case, or move next)
                # Here we simply refresh pagination state
                pass
            except Exception as e:
                logger.warning(f"Failed to resume category {category_id}: {e}. Restarting.")
                start_from_scratch = True
        else:
            if last_processed_page > 0:
                logger.warning(
                    f"Table size changed (Saved: {saved_total_pages}, Current: {current_table_size_pages}). Restarting category."
                )
            start_from_scratch = True

    if start_from_scratch:
        logger.info(f"Starting Category {category_id} from scratch (cleaning chunks).")
        delete_chunks(category_id)
        # Ensure we are at page 1 (Angular might stay on last page if we just reloaded)
        # Usually get(url) resets, but set_max_table_size might shift things.
        # Since we just loaded the page, we should be at 1.

    # --- Scraping Loop ---
    pages, next_button, _ = get_pages(driver)
    logger.info(f"Pagination initialized. Current: {pages['current']} | Last: {pages['last']}")

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

        # Click Next
        scroll(driver, next_button)
        highlight(driver, next_button, color="green")
        next_button.click()
        sleep(1)  # Wait for Angular

        pages, next_button, _ = get_pages(driver)
        sleep(0.5)

        # Stuck check
        if previous_page == pages["current"]:
            logger.warning(f"Page stuck at {pages['current']}. Stopping.")
            break

    logger.info(f"Category {category_id} processing complete. Total rows saved: {search_size}")


def scrap_unit_category(category_id: int, force: bool = False) -> None:
    """
    Orchestrates the scraping of a single category with pre-fetch validation.
    """
    logger.info(f"--- Starting Process for Category {category_id} ---")

    meta = get_fetch(category_id)
    if meta:
        logger.info(f"Category {category_id}: Expecting {meta['total']} items.")
    else:
        logger.warning(f"Skipping Category {category_id}: No fetch metadata found.")
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
    Navigates to the first and last page to estimate data volume.
    """
    url = CATEGORIES_URL % str(category_id)
    logger.info(f"Fetching metadata for Category {category_id} | URL: {url}")

    driver.get(url)

    max_table_size = set_max_table_size(driver)

    # Needs a try/except for empty categories
    try:
        pages, _, last_button = get_pages(driver)
    except Exception:
        logger.warning(f"Category {category_id} seems empty or failed to load pagination.")
        return [category_id, max_table_size, 0, 0]

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
        max_table_size,
        pages["last"],
        total_items,
    ]


# ====== Orchestration (Execution) ======


def scrap_categories(n_threads: int = 1, force: bool = False) -> None:
    """
    Orchestrates the parallel scraping of all categories.

    Args:
        n_threads (int): Number of concurrent threads.
        force (bool): If True, deletes all previous chunks and starts fresh.
                      If False, attempts to resume based on progress.
    """
    logger.info("--- Starting Scraping Pipeline ---")

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

    logger.info("Thread pool finished. Consolidating data...")

    join_chunks(force=force)

    logger.info("Scraping Pipeline Finished")


def fetch_categories() -> None:
    """
    Orchestrates metadata fetching for all categories.
    """
    logger.info("--- Setup Fetch Execution ---")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    options = get_firefox_options()

    fetch_columns = ["id", "table_size", "pages", "total"]
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

        fetch_df = pd.DataFrame(fetch_values, columns=fetch_columns)
        fetch_df.to_csv(INDEX_FETCHED, index=False)

        logger.info(f"Fetch complete. Metadata saved to {INDEX_FETCHED}")

    except Exception as e:
        logger.critical(f"Critical error during categories fetch: {e}")
        raise


# ====== SCRIPT ENTRY POINT ======

app = typer.Typer(
    help="CLI for get drug informations from ANVISA.",
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
):
    """
    Runs the ANVISA drug listing scraper pipeline.
    """
    try:
        if update:
            fetch_categories()

        if check:
            check_index()
            return

        logger.info(f"Starting pipeline (Threads: {n_threads}, Force: {force})...")
        scrap_categories(n_threads, force=force)

        # Optional final check
        check_index()

        logger.info(f"Pipeline execution complete. Log: {log_file_path.resolve()}")

    except Exception as e:
        logger.exception(f"Fatal error during pipeline execution: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    from drugslm.utils.logging import get_log_path, setup_logging

    log_file_path = get_log_path(__file__)
    setup_logging(log_file_path)

    app()
