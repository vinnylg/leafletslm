from dagster import Definitions

from drugslm.scraper.selenium import webdriver_resource
from drugslm.utils.logging import get_log_path, setup_logging

setup_logging(get_log_path(__file__))

defs = Definitions(
    resources={
        "selenium": webdriver_resource,
    },
)
