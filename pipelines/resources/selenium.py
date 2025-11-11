"""
Dagster Utilities - Selenium Resource
======================================

This module defines a generic, reusable Dagster Resource for managing
the life cycle of a remote Selenium WebDriver.

Purpose:
    - Provide a configurable '@resource' for Selenium.
    - Read the global constant 'HUB_URL' directly from 'leaflets.config'.
    - Allow 'browser_type' to be set via Dagster's config system.
    - Perform connection, validation, and teardown.

Philosophy:
    KISS - Keep It Simple. Zen of Python (PEP20)

Author: Vinícius de Lima Gonçalves
Documentation: Gemini 2.5 Pro (Student), Vinícius de Lima Gonçalves
"""

from dagster import resource
from retry import retry
from selenium import webdriver

from leaflets.config import HUB_URL
from leaflets.utils.selenium import (
    get_firefox_options,
    validate_driver_connection,
)


@retry(tries=3, delay=10, backoff=2)
@resource(description="Manages the life cycle of a remote Selenium WebDriver.")
def selenium_browser(context):
    """
    Manages the setup, validation, and teardown of a remote WebDriver.

    This resource is configurable for browser type and uses the
    global HUB_URL constant.
    """
    log = context.log
    options = get_firefox_options()

    driver = None
    # Use the imported constant directly
    log.info(f"Attempting to connect to Selenium Hub at {HUB_URL}...")
    try:
        driver = webdriver.Remote(
            command_executor=HUB_URL,
            options=options,
        )

        validate_driver_connection(driver)

        log.info(f"Connection successful. Session ID: {driver.session_id}")
        yield driver

    except Exception as e:
        log.error(f"Failed to initialize or validate WebDriver: {e}")
        raise
    finally:
        if driver:
            log.info(f"Closing Selenium session: {driver.session_id}")
            driver.quit()
