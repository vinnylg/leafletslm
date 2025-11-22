from dagster import Definitions

from drugslm.scraper.selenium import webdriver_resource
from drugslm.utils.logging import setup_logging

setup_logging()

defs = Definitions(
    resources={
        "selenium": webdriver_resource,
    },
)
