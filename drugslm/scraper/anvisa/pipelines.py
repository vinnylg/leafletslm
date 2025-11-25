from dagster import (
    DynamicOut,
    DynamicOutput,
    In,
    List,
    OpExecutionContext,
    Out,
    job,
    op,
)
from selenium.webdriver.remote.webdriver import WebDriver

from drugslm.scraper.anvisa.build_index import (
    fetch_categories,
    get_fetched,
    join_category_pages,
    scrap_pages,
)


@op(required_resource_keys={"selenium"}, out=DynamicOut())
def op_fetch_metadata(context: OpExecutionContext):
    """
    Executes metadata fetching and generates dynamic outputs for each non-empty category.
    This replaces the sequential loop, allowing Dagster to parallelize the scraping step.
    """
    driver: WebDriver = context.resources.selenium

    context.log.info("Starting Metadata Fetch...")

    # Executes the original logic from index.py
    # fetch_categories saves the CSV, so we only need the return to orchestrate
    df = fetch_categories(driver)

    if df is None or df.empty:
        context.log.warning("No categories returned from fetch.")
        return

    # Iterates over found categories to create dynamic tasks
    for _, row in df.iterrows():
        category_id = int(row["category_id"])
        category_size = int(row["category_size"])

        # Optimization: If size is 0, do not create a scrape task
        if category_size > 0:
            context.log.info(f"Scheduling Category {category_id} ({category_size} items)")
            yield DynamicOutput(
                value=category_id,
                mapping_key=str(category_id).replace(
                    "-", "_"
                ),  # mapping_key must be a safe string
            )
        else:
            context.log.info(f"Skipping scheduling for Category {category_id} (Empty)")


@op(required_resource_keys={"selenium"}, ins={"category_id": In(int)}, out=Out(str))
def op_scrape_category(context: OpExecutionContext, category_id: int):
    """
    Receives an injected driver and scrapes a specific category.
    Returns a status string to be collected by the join step.
    """
    driver: WebDriver = context.resources.selenium

    # Double check against fetch metadata
    expected_size = get_fetched(category_id)
    context.log.info(
        f"Starting Scrape for Category {category_id}. Expected items: {expected_size}"
    )

    # Calls the core logic from index.py directly
    _, saved_items = scrap_pages(driver, category_id)

    msg = f"Finished Category {category_id}. Saved {saved_items} items."
    context.log.info(msg)

    return msg


@op(ins={"scraped_results": In(List[str])})
def op_consolidate_results(context: OpExecutionContext, scraped_results: list):
    """
    Consolidates all individual page pickle files into a single DataFrame.
    This runs only after all 'op_scrape_category' tasks are finished.

    Args:
        scraped_results: List of messages from previous steps (used mainly to enforce dependency).
    """
    context.log.info(f"All {len(scraped_results)} categories finished. Starting consolidation...")

    final_path = join_category_pages()

    if final_path:
        context.log.info(f"Consolidation complete. File saved at: {final_path}")
    else:
        context.log.warning("Consolidation failed or no files found.")


@job(resource_defs={"selenium": "selenium"})  # Will be resolved in definitions.py
def anvisa_index_scraper_job():
    """
    Job that orchestrates the entire pipeline:
    1. Fetch metadata (Sequential)
    2. Scrape categories (Parallel/Dynamic Fan-out)
    3. Consolidate results (Fan-in)
    """
    # 1. Execute Fetch and get a list of valid IDs
    category_ids = op_fetch_metadata()

    # 2. Map the scrape operation to each returned ID
    # .collect() gathers all results into a list, waiting for all to finish
    scrape_results = category_ids.map(op_scrape_category).collect()

    # 3. Join everything after scrape is done
    op_consolidate_results(scrape_results)
