"""ANVISA Data Source Configuration.

This module acts as the configuration entry point for the ANVISA data source
subpackage. It defines global constants, file paths, and remote URLs used
across the scraping and processing modules.

Scope:
    This module is responsible for:
    - Centralizing URL definitions for ANVISA portals and open datasets.
    - Defining the directory structure for raw data storage within the ANVISA scope.
    - Exporting constants for use in sibling modules (e.g., categories scraper).

Authors:
    - Vinícius de Lima Gonçalves
"""

from drugslm.config import EXTERNAL, RAW

DADOS_ABERTOS_URL = "https://dados.anvisa.gov.br/dados/DADOS_ABERTOS_MEDICAMENTOS.csv"
"""str: Direct URL to the ANVISA Open Data CSV file containing registered drugs."""

DADOS_ABERTOS = EXTERNAL / "anvisa" / "dados_abertos.csv"
"""Path: Local file path where the Open Data CSV is stored after download."""

ANVISA_DIR = RAW / "anvisa"
"""Path: Root directory for storing raw data scraped specifically from the ANVISA query portal."""

ANVISA_URL = "https://consultas.anvisa.gov.br/#/bulario/q/"
"""str: Base URL for the ANVISA 'Bulário Eletrônico' (Electronic Leaflet) query interface."""