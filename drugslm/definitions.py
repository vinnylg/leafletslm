from dagster import Definitions

from drugslm.scraper.anvisa.pipelines import anvisa_catalog, anvisa_metadata
from drugslm.scraper.selenium import webdriver_resource

defs = Definitions(
    assets=[
        anvisa_metadata,
        anvisa_catalog,
    ],
    resources={
        "selenium": webdriver_resource,
    },
)
