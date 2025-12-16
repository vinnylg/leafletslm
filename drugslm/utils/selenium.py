"""
Selenium WebDriver Utilities
============================

This module provides utilities for managing Selenium WebDriver connections,
specifically for remote drivers connected to a Selenium Hub.

It includes:
- A context manager 'webdriver_manager' for safe setup/teardown.
- A 'validate_driver_connection' health check function.
- Helper functions for UI interaction and configuration loading.
"""

from contextlib import contextmanager
import logging
import os
from typing import Iterator, Literal, Union

from retry import retry
from selenium import webdriver
from selenium.common.exceptions import JavascriptException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from drugslm.config.tree import default_configs

DEFAULT_HUB_URL = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444/wd/hub")

logger = logging.getLogger(__name__)


@retry(tries=3, delay=10, backoff=1.5)
def _create_driver(
    hub_url: str,
    browser_options: Union[FirefoxOptions, ChromeOptions],
) -> WebDriver:
    """
    Handles the setup (initialization, validation) of a Selenium driver.

    The @retry decorator will attempt the *entire setup and validation* phase
    multiple times if it fails (e.g., hub startup race conditions).

    Args:
        hub_url (str): The URL of the Selenium Hub.
        browser_options (FirefoxOptions | Any): The Selenium options object
            containing browser-specific capabilities.

    Returns:
        WebDriver: An initialized and validated WebDriver instance.
    """
    logger.info(f"Attempting to connect to Selenium Hub at {hub_url}...")

    driver = webdriver.Remote(
        command_executor=hub_url,
        options=browser_options,
    )

    validate_driver_connection(driver)

    logger.info(f"Connection successful. Session ID: {driver.session_id}")
    return driver


@contextmanager
def webdriver_manager(
    hub_url: str = DEFAULT_HUB_URL,
    browser: Literal["firefox", "chrome"] = "firefox",
) -> Iterator[WebDriver]:
    """
    Manages the life cycle of a remote WebDriver as a context manager.

    Args:
        hub_url (str): The URL of the Selenium Hub. Defaults to DEFAULT_HUB_URL.
        browser (Literal["firefox", "chrome"]): The browser name to be used. Default "firefox".

    Yields:
        WebDriver: A live, validated Selenium WebDriver instance.

    Raises:
        Exception: Propagates any exception during connection, validation,
            or if the 'retry' attempts fail.
    """
    driver = None

    if browser == "firefox":
        browser_options = get_firefox_options()
    elif browser == "chrome":
        raise NotImplementedError("Chrome not yet implemented")
    else:
        raise Exception(f"{browser} may be firefox or chrome")

    try:
        driver = _create_driver(hub_url, browser_options)
        yield driver

    except Exception as e:
        logger.error(f"Exception occurred during driver usage: {str(e).splitlines()[0]}")
        raise
    finally:
        if driver:
            logger.info(f"Closing Selenium session: {driver.session_id}")
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
        logger.error(f"Driver health check failed: {str(e).splitlines()[0]}")
        raise


def get_firefox_options() -> FirefoxOptions:
    """
    Loads Firefox configurations from the config object and returns the options.

    Returns:
        FirefoxOptions: A configured options object ready for the GeckoDriver,
            populated with arguments and preferences from the YAML/JSON file.

    Raises:
        FileNotFoundError: If the config object is None or the underlying file is missing.
        ValueError: If the file format is unsupported (handled by .load()).
    """

    if default_configs.browser.firefox is None:
        raise FileNotFoundError("Configuration tree is None")

    config = default_configs.browser.firefox.load()
    options = FirefoxOptions()

    arguments = config.get("arguments", [])
    if arguments:
        logger.info(f"Adding {len(arguments)} arguments to FirefoxOptions.")
        for arg in arguments:
            options.add_argument(arg)

    preferences = config.get("preferences", {})
    if preferences:
        logger.info(f"Setting {len(preferences)} preferences for FirefoxOptions.")
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
        logger.info(f"Could not highlight element: {str(e).splitlines()[0]}")
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
        logger.info(f"Could not scroll to element: {str(e).splitlines()[0]}")
        pass
