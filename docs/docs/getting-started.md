# Getting Started

This guide describes how to set up the development environment for a clean install, including dependency management and running the initial data extraction pipelines.

## Prerequisites

- **Docker & Docker Compose**: For running infrastructure (Selenium Grid, Databases).
- **uv**: An extremely fast Python package installer and resolver.
- **Python 3.12+**

## Running the Scraper (CLI)

This project uses **Typer** for CLI commands. To run the ANVISA drug listing scraper:

```bash
python -m drugslm.scraper.anvisa.index --help
```
