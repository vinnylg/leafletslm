"""
Global configuration module for the drugslm project.

This module handles:
1. Environment variable loading (for Project/Docker infrastructure).
2. Global directory definitions (Data, Logs, Reports).
3. Access to static configuration files via the 'settings' object.
"""

from drugslm import PROJECT_ROOT

# Defines the location of specifics environment files
SECRETS_DIR = PROJECT_ROOT / ".secrets"

# Global Directory Definitions
DATA = PROJECT_ROOT / "data"

RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"

LOGS = PROJECT_ROOT / "logs"
REPORTS = PROJECT_ROOT / "reports"
FIGURES = REPORTS / "figures"


__all__ = [
    "RAW",
    "INTERIM",
    "PROCESSED",
    "EXTERNAL",
    "LOGS",
    "REPORTS",
    "FIGURES",
    "SECRETS_DIR",
]
