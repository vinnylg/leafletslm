"""
Dagster Pipeline - ANVISA Definitions
=====================================

This module is the main entry point for the ANVISA Dagster project.

Purpose:
    - Aggregate all definitions into a single 'Definitions' object.
    - Imports the single, generic 'anvisa_scrape_job' from 'jobs.py'.
    - Imports the single, generic 'selenium_resource' from 'utils'.
    - Binds the resource key "selenium" (used by the Ops) to the
        'selenium_resource' definition.
    - The choice of browser (Chrome/Firefox) is *not* defined here;
        it is provided as run-level configuration at launch time.

Philosophy:
    KISS - Keep It Simple. Zen of Python (PEP20)

Author: Vinícius de Lima Gonçalves
Documentation: Gemini 2.5 Pro (Student), Vinícius de Lima Gonçalves
"""

from dagster import Definitions

from pipelines.resources.selenium import selenium_browser

# from .jobs import anvisa_scrape_job

defs = Definitions(resources={"selenium": selenium_browser})
