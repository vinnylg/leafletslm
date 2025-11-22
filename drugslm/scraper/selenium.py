"""
Selenium WebDriver Utilities
============================

This module provides utilities for managing Selenium WebDriver connections,
specifically for remote drivers connected to a Selenium Hub.

It includes:
- A context manager 'webdriver_context' for safe setup/teardown.
- A Dagster resource 'webdriver_resource'.
- A 'validate_driver_connection' health check function.
- Helper functions for UI interaction and configuration loading.
"""

from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, Union

from dagster import InitResourceContext, resource
from retry import retry
from selenium import webdriver
from selenium.common.exceptions import JavascriptException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import yaml

from drugslm.config import FIREFOX_OPTIONS, HUB_URL

logger = logging.getLogger(__name__)


@retry(tries=3, delay=10, backoff=1.5)
def _create_driver(browser_options: Union[FirefoxOptions, Any]) -> WebDriver:
    """
    Handles the setup (initialization, validation) of a Selenium driver.

    The @retry decorator will attempt the *entire setup and validation* phase
    multiple times if it fails (e.g., hub startup race conditions).

    Args:
        browser_options (FirefoxOptions | Any): The Selenium options object
            containing browser-specific capabilities.

    Returns:
        WebDriver: An initialized and validated WebDriver instance.
    """
    logger.info(f"Attempting to connect to Selenium Hub at {HUB_URL}...")

    driver = webdriver.Remote(
        command_executor=HUB_URL,
        options=browser_options,
    )

    validate_driver_connection(driver)

    logger.info(f"Connection successful. Session ID: {driver.session_id}")
    return driver


@contextmanager
def webdriver_manager(browser_options: Union[FirefoxOptions, Any]) -> Iterator[WebDriver]:
    """
    Manages the life cycle of a remote WebDriver as a context manager.

    Args:
        browser_options (FirefoxOptions | Any): The Selenium options object
            (e.g., FirefoxOptions, ChromeOptions) to be used.

    Yields:
        WebDriver: A live, validated Selenium WebDriver instance.

    Raises:
        Exception: Propagates any exception during connection, validation,
            or if the 'retry' attempts fail.
    """
    driver = None
    try:
        driver = _create_driver(browser_options)
        yield driver

    except Exception as e:
        logger.error(f"Exception occurred during driver usage: {e}")
        raise
    finally:
        if driver:
            logger.info(f"Closing Selenium session: {driver.session_id}")
            driver.quit()


@resource(description="Manages the life cycle of a remote Selenium WebDriver.")
def webdriver_resource(context: InitResourceContext) -> Iterator[WebDriver]:
    """
    Dagster resource that manages the setup, validation, and teardown of a remote WebDriver.

    This resource uses the global HUB_URL constant and loads default Firefox options.

    Args:
        context (InitResourceContext): The Dagster resource context.

    Yields:
        WebDriver: A live, validated Selenium WebDriver instance.
    """
    # Note: context.log uses Dagster's internal logger, while other functions use Loguru.
    log = context.log

    # Assuming standard flow, we might want to catch config errors early
    try:
        browser_options = get_firefox_options()
    except Exception as e:
        log.error(f"Failed to load browser options: {e}")
        raise

    driver = None
    log.info(f"Attempting to connect to Selenium Hub at {HUB_URL}...")

    try:
        # Reuse the retry logic from _create_driver
        driver = _create_driver(browser_options)
        yield driver

    except Exception as e:
        log.error(f"Failed to initialize or validate WebDriver in resource: {e}")
        raise
    finally:
        if driver:
            log.info(f"Closing Selenium session: {driver.session_id}")
            driver.quit()


def validate_driver_connection(driver: WebDriver) -> bool:
    """
    Performs a basic health check on an active WebDriver instance.

    It attempts to load a known page (google.com) and verifies
    that basic functionality (JS execution, element finding) is working.

    Args:
        driver (WebDriver): The WebDriver instance to test.

    Returns:
        bool: True if the validation is successful.

    Raises:
        Exception: If any assertion or step in the validation fails.
    """
    try:
        logger.info("Validating driver connection...")
        driver.get("https://www.google.com")

        assert "Google" in driver.title, "Google.com did not load correctly."

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "q")))

        logger.info("Driver connection validated successfully.")
        return True
    except Exception as e:
        logger.error(f"Driver health check failed: {e}")
        raise


def get_firefox_options(config_path: Union[Path, str] = FIREFOX_OPTIONS) -> FirefoxOptions:
    """
    Loads Firefox configurations from a YAML file and returns a configured object.

    Args:
        config_path (Path | str): The path to the YAML configuration file.
            Defaults to the global FIREFOX_OPTIONS constant.

    Returns:
        FirefoxOptions: The configured options object for GeckoDriver.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        yaml.YAMLError: If the file cannot be parsed.
    """
    config_file = Path(config_path)
    if not config_file.is_file():
        logger.error(f"Configuration file not found at: {config_file}")
        raise FileNotFoundError(f"Configuration file not found at: {config_file}")

    logger.debug(f"Loading Firefox options from: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    options = FirefoxOptions()

    arguments = config.get("arguments", [])
    if arguments:
        logger.debug(f"Adding {len(arguments)} arguments to FirefoxOptions.")
        for arg in arguments:
            options.add_argument(arg)

    preferences = config.get("preferences", {})
    if preferences:
        logger.debug(f"Setting {len(preferences)} preferences for FirefoxOptions.")
        for name, value in preferences.items():
            options.set_preference(name, value)

    return options


def highlight(driver: WebDriver, element: WebElement, color: str = "green") -> None:
    """
    Highlights a specific WebElement by drawing a border around it using JS.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        element (WebElement): The target Selenium WebElement instance.
        color (str, optional): The border color. Defaults to "green".
    """
    try:
        driver.execute_script(f"arguments[0].style.border='3px solid {color}';", element)
        # sleep(1)
    except JavascriptException as e:
        # Fail silently if highlighting isn't critical, but log trace for debug
        logger.debug(f"Could not highlight element: {e}")
        pass


def scroll(driver: WebDriver, element: WebElement) -> None:
    """
    Scrolls the page to bring the specified WebElement into view using JS.

    Args:
        driver (WebDriver): The active Selenium WebDriver instance.
        element (WebElement): The target Selenium WebElement instance.
    """
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element
        )
        # sleep(1)
    except JavascriptException as e:
        # Fail silently if scrolling isn't critical, but log trace for debug
        logger.debug(f"Could not scroll to element: {e}")
        pass
