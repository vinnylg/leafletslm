"""
Selenium WebDriver Utilities
============================

This module provides utilities for managing Selenium WebDriver connections,
specifically for remote drivers connected to a Selenium Hub.

It includes:
- A context manager 'managed_webdriver' for safe setup/teardown.
- A 'validate_driver_connection' health check function.

Author: Vinícius de Lima Gonçalves
Documentação: Gemini 2.5 Pro (Student), Vinícius de Lima Gonçalves
"""

from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Any, Dict, Iterator

from retry import retry
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import yaml

from lslm.config import FIREFOX_OPTIONS, HUB_URL

log = logging.getLogger(__name__)


@contextmanager
@retry(tries=3, delay=10, backoff=2)
def managed_webdriver(browser_options) -> Iterator[WebDriver]:
    """
    Manages the life cycle of a remote WebDriver as a context manager.

    This function handles the setup (initialization, validation) and
    teardown (quit) of a Selenium driver. The @retry decorator
    will attempt the *entire setup and validation* phase multiple times
    if it fails (e.g., hub startup race conditions).

    Args:
        browser_options: The Selenium options object (e.g.,
            FirefoxOptions, ChromeOptions) to be used.

    Yields:
        WebDriver: A live, validated Selenium WebDriver instance.

    Raises:
        Exception: Propagates any exception during connection, validation,
            or if the 'retry' attempts fail.
    """
    driver = None
    log.info(f"Attempting to connect to Selenium Hub at {HUB_URL}...")
    try:
        driver = webdriver.Remote(command_executor=HUB_URL, options=browser_options)
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
        log.info("Validating driver connection...")
        driver.get("https://www.google.com")

        assert "Google" in driver.title, "Google.com did not load correctly."

        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "q")))

        log.info("Driver connection validated successfully.")
        return True
    except Exception as e:
        log.error(f"Driver health check failed: {e}")
        raise


def get_firefox_options(config_path: Path | str = FIREFOX_OPTIONS) -> FirefoxOptions:
    """
    Carrega as configurações do Firefox a partir de um arquivo YAML e retorna
    um objeto FirefoxOptions configurado.

    Args:
        config_path (Path | str): O caminho para o arquivo de configuração YAML.

    Returns:
        FirefoxOptions: Objeto de opções para o GeckoDriver.

    Raises:
        FileNotFoundError: Se o arquivo de configuração não for encontrado.
    """
    config_file = Path(config_path)
    if not config_file.is_file():
        raise FileNotFoundError(f"Arquivo de configuração não encontrado em: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    options = FirefoxOptions()

    # Adiciona os argumentos da lista 'arguments'
    arguments = config.get("arguments", [])
    if arguments:
        for arg in arguments:
            options.add_argument(arg)

    # Adiciona as preferências do dicionário 'preferences' (específico do Firefox)
    preferences = config.get("preferences", {})
    if preferences:
        for name, value in preferences.items():
            options.set_preference(name, value)

    return options
