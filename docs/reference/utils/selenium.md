# Selenium Infrastructure

Utilities for managing WebDriver connections, Dagster resources, and browser interactions specific to the Scraper module.

## Lifecycle Management

Tools to create, validate, and destroy WebDriver sessions connecting to the Selenium Grid.

> Perhaps Selenium could be placed in the `utils` folder, and not the `sources` folder. Why? Here it's only present in the `sources` folder, but Selenium could be used in automated tests in the future. I'll leave that to my future self.

::: drugslm.utils.selenium
