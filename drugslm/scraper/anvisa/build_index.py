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


def set_max_table_size(driver: WebDriver) -> None:
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
                    return int(btn.text.strip())

                btn.click()
                logger.info(f"Successfully set page count to: {btn.text}")
                return int(btn.text.strip())

            except WebDriverException as e:
                logger.warning(
                    f"Failed to click page count option '{btn.text}'. Trying previous option. Error: {e}"
                )
                continue

    except Exception as e:
        logger.critical(f"element for set_max_table_size not found: {e}")


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


def save_chuck(data: list[list], category_id: int, page_num: int) -> int:  # @gemini ok
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


def join_chunks(force: bool = False) -> None:  # @gemini todo
    """
    Consolidates all individual page pickle files into a single DataFrame.

    Returns:
        Path: The path to the consolidated file, or None if no files found.
    """

    # @gemini: estava pensando, independente do remain ser usado ou não, vamos supor que deu tudo certo e que tenho um pkl consolidado. Mas eu criei uma rotina que toda semana roda o fetch pra ver se tem coisa nova. Daí o fetch mostrou que a categoria 10 tem 3 novos items. O site não possui uma lógica de ordenação visivel, creio eu que muda diariamente. Eu sei que se for isso eu estou perdendo tempo com essa lógica de remain/update. Mas é também um amadurecimento na área.
    # Indo direto ao ponto. Ao invés de refazer tudo, posso só refazer a categoria 10 que modificou. Aproveitando, se diminuir o número de itens na categoria em teoria não é para dar problema, já que o dado continua valido. Talvez o link extraido não funcione mais, porém não preciso apagar da tabela ou da base de pdf. Mas talvez seja interessante colocar uma coluna no dataframe que indique isso.
    # detalhando melhor: dois modos de uso: a função vai sobrescrever o arquivo INDEX_TABLE com um novo usando os chuncks
    # ou a função vai fazer uma interseção do INDEX_TABLE antigo com o gerado pelos chunks.
    # é bem provavel que a coluna da tabela no site Expediente seja única. Não sei se ela muda quando um medicamento é renovado ou algo do tipo. Senão daria para usar multiindex com o nome do medicamento e a empresa (o campo empresa divide 'nome - cnpj'. É fácil separar mas nesse estágio a ideia é modificar o minimo possível os dados (RAW/Bronze))
    # é uma tarefa fácil mas se eu não terminar isso logo eu não vou ter paz, porque quanto mais tempo eu fica mexendo aqui mais coisa não tão importante eu vou achar pra faz e tangenciar do principal.

    all_files = list(INDEX_CHUNKS.glob("*.pkl"))

    if not all_files:
        logger.warning("No pickle files found to consolidate in {INDEX_CHUNKS}.")
        return

    logger.info(f"{len(all_files)} files found in {INDEX_CHUNKS}")

    all_tables = pd.concat([pd.read_pickle(f) for f in all_files], ignore_index=True)

    if force:
        all_tables.to_pickle(INDEX_TABLE)
        all_tables.to_csv(INDEX_TABLE.with_suffix(".csv"), index=False)

    else:
        # @gemini pega o get_index() e faz um join com all_tables. Como all_tables é mais atual, all_tables sobrescreve linhas iguais no get_index() com base id definido
        pass

    logger.info(f"Consolidation complete. Saved {len(all_tables)} rows to {INDEX_TABLE}")

    delete_chunks()


def delete_chunks(
    category_id: int | None = None,
):  # @gemini todo: aqui só colocar docstrings e melhorar/aumentar os logs?
    all_files = list(INDEX_CHUNKS.glob(f"{category_id or ''}*.pkl"))

    try:
        for f in all_files:
            f.unlink()

        if not len(list(INDEX_CHUNKS.glob())):
            INDEX_CHUNKS.rmdir()

        logger.info("Remove chunks files complete")
    except Exception as e:
        logger.error(f"Error to delete files: {e}")


def save_progress(
    category_id: int, pages: dict, saved_size: int
) -> None:  # @gemini todo: eu modifiquei um pouco
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
            if not INDEX_PROGRESS.exists():
                out.write("timestamp,category_id,current_page,last_page,saved_size\n")

            out.write(
                f"{timestamp},{category_id},{pages['current']},{pages['last']},{saved_size}\n"
            )


def get_index() -> pd.DataFrame:  # @gemini todo: colocar docstrings e logs. Algo mais?
    try:
        return pd.read_pickle(INDEX_TABLE)
    except Exception as e:
        logger.error(f"{INDEX_TABLE} doesn't exist or not could be read {e}")
        raise


def get_fetch(
    category_id: int | None = None,
) -> (
    pd.DataFrame | int | None
):  # @gemini todo: por mais que seja uma função meio que multifuncional, ela retorna coisas distintas demais. Acho que da para manter a ideia de conseguir filtraar qual categoria, mas ao invés de retornar um int retorne a row/serie. Quem chamou que lide com a lógica de pegar o valor desejado ou com um df vazio.
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

        return int(row.iloc[0])  # @gemini acho essa linha estranha

    except Exception as e:
        logger.error(f"Error reading fetched categories CSV: {e}")
        return None


def check_index() -> (
    int
):  # @gemini todo: Acho importante uma lógica semelhante ao get_fetch(category_id: int | None = None) -> pd.DataFrame | int | None: Como essa função vai ser usada para saber se falta algo, o diff é importante
    """
    Checks the consistency between the local index and the ANVISA database.
    """

    # @gemini outra coisa, o check_index só está sendo usado quando roda o run/typer com --check, não sei exatamente aonde mais colocar ele.

    logger.info("--- Starting Index Check ---")

    # 1. Carrega o índice local (O que nós temos)
    try:
        df_local = get_index()
        local_size = len(df_local)
        logger.info(f"Local index found: {local_size} records.")
    except Exception:
        # @gemini analisando todo o código, tem possíbilidade de ocorrer algum erro na qual os chunks não são concatenados no dataframe final? Se sim, o que é melhor fazer, juntar tudo e apagar os chunks ou só apagar eles? onde seria melhor colocar essa lógica?
        logger.warning(f"Local index ({INDEX_TABLE}) not found or unreadable.")
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


def get_last_processed_page(category_id) -> int:  # @gemini
    ## le dataframe from INDEX_PROGRESS
    ## o dataframe tem essas colunas category_id,timestamp,current_page,next_page,last_page,saved_size
    ## a ideia é que esse arquivo não seja apagado ou modificado manualmente
    ## mas muita coisa pode ir se repetindo.
    ## A informação mais importante no momento é qual foi a última pagina processada do category_id
    ## O timestamp vai ser usado para pegar o ultimo registro

    last_page, table_size = 0
    return last_page, table_size


def goto_last_processed_page(
    driver: WebDriver, target_page: int
) -> None:  # @gemini acho que tá okay.
    """
    Navigates to the target_page using a sliding window strategy.
    Optimizes the path by choosing to start from the beginning or the end.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        target_page (int): The page number to reach.
    """
    try:
        # 1. Get total pages to decide strategy
        last_page_elem = driver.find_element(By.XPATH, XPATH_LAST_PAGE)
        total_pages = int(last_page_elem.text.strip())

        logger.info(f"Navigating to processed page {target_page} (Total: {total_pages})...")

        # 2. Strategy: Go to LAST page first if target is in the second half
        if target_page > (total_pages / 2):
            logger.debug("Target is closer to the end. Jumping to Last Page.")
            last_page_elem.click()
            # Wait for the jump
            WebDriverWait(driver, 10).until(
                lambda d: int(d.find_element(By.XPATH, XPATH_CURRENT_PAGE).text) == total_pages
            )

        # 3. Sliding Window Loop
        while True:
            current_elem = driver.find_element(By.XPATH, XPATH_CURRENT_PAGE)
            current_page = int(current_elem.text.strip())

            if current_page == target_page:
                logger.info(f"Arrived at target page {current_page}.")
                break

            # Find all visible page number links (exclude prev/next/first/last/more buttons)
            # Logic: Get all 'a' in pagination, filter those that are numbers
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

            # Decision Logic
            if target_page in visible_pages:
                # Target is visible, click directly
                visible_pages[target_page].click()
                next_expected = target_page
            elif current_page < target_page:
                # Target is ahead, click the max visible to slide right
                next_expected = max(visible_pages.keys())
                visible_pages[next_expected].click()
            else:
                # Target is behind, click the min visible to slide left
                next_expected = min(visible_pages.keys())
                visible_pages[next_expected].click()

            # Wait for page update
            WebDriverWait(driver, 10).until(
                lambda d: int(d.find_element(By.XPATH, XPATH_CURRENT_PAGE).text) == next_expected
            )

    except Exception as e:
        logger.error(f"Failed to navigate to last processed page: {e}")
        raise


# ====== Scraper Core Business Logic (Process) ======


def scrap_pages(
    driver: WebDriver, category_id: int, force: bool = False
) -> None:  # @gemini aqui a magica do force acontece
    """
    Iterates through all pages of a specific regulatory category, extracting and saving data.

    This function handles pagination navigation, saves checkpoints for every page found,
    and logs the execution progress.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        category_id (int): The ID of the regulatory category to scrape.
    """
    search_size = 0

    url = CATEGORIES_URL % str(category_id)
    logger.info(f"Accessing ANVISA search page: {url}")

    driver.get(url)

    table_size = set_max_table_size(driver)

    # @gemini: por mais que esse bloco try/except e if/else esteja lógicamente correto com o que eu quero, não to gostando dele. Tá mto repetitivo.
    try:
        if not force:
            last_page_number, previous_table_size = get_last_processed_page(category_id)

            if previous_table_size != table_size:
                # logger.error("não tem como continuar, vai dar números de páginas diferente , apagando tudo e começando do zero. Clearing previous temporary chunks for {category_id} before starting.")
                delete_chunks(category_id)

            goto_last_processed_page(driver, last_page_number)
            _, next_button, _ = get_pages(driver)
            next_button.click()
        else:
            logger.info(
                f"keep=False: Clearing previous temporary chunks for {category_id} before starting."
            )
            delete_chunks(category_id)
    except Exception as e:
        logger.error(
            f"Some error occurs {e}. Clearing previous temporary chunks for {category_id} before starting."
        )
        delete_chunks(category_id)

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


def scrap_unit_category(category_id: int, force: bool = False) -> None:
    """
    Orchestrates the scraping of a single category with pre-fetch validation.
    """
    logger.info(f"--- Starting Process for Category {category_id} ---")

    if expected_size := get_fetch(category_id):
        logger.info(f"Category {category_id}: Expecting {expected_size} items.")
    else:
        logger.warning(f"Skipping Category {category_id}: Fetch is {expected_size}")
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
        list: [category_id, total_pages, estimated_total_items].
    """
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


def scrap_categories(n_threads: int = 1, force: bool = False):  # @gemini logs e docstrings
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
    logger.info("--- Starting Scraping Pipeline ---")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        executor.map(
            partial(
                scrap_unit_category,
                force=force,
            ),
            CATEGORIES,
        )

    logger.info(
        "Thread pool execution finished. Consolidating data chunks and check final data..."
    )

    join_chunks(force)

    logger.info("Scraping Pipeline Finished")


def fetch_categories():
    """
    Orchestrates metadata fetching for all categories listed in CATEGORIES.
    """
    logger.info("--- Setup Fetch Execution ---")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    options = get_firefox_options()

    fetch_columns = [
        "id",
        "table_sizepages",
        "total",
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
            help="Force execution to start from zero.",
            show_default=False,
        ),
    ] = False,  # gemini todo: outra vez mudando nome de variavel, mas estava pensando que o melhor seria que o comportamento do remain == True fosse o padrão. semanticamente force == False é remain == True. No fim mudei o conceito e a ordem nos ifs
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

        scrap_categories(n_threads, force, update)

        logger.info(f"Pipeline execution complete. Log: {log_file_path.resolve()}")

    except Exception as e:
        logger.exception(f"Fatal error during pipeline execution: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    from drugslm.utils.logging import get_log_path, setup_logging

    log_file_path = get_log_path(__file__)
    setup_logging(log_file_path)

    app()
