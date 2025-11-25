# Dagster Pipelines

Orchestration layer for the ANVISA scraper. This module defines the atomic Operations (Ops) and the aggregated Job that manages the execution flow, parallelism, and resource allocation.

## Index Scraper Job

The central pipeline that connects metadata fetching, dynamic parallel scraping, and data consolidation.

::: drugslm.scraper.anvisa.pipelines
