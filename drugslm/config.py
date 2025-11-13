import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

HUB_URL = os.getenv("HUB_URL")
BROWSER_NODES = int(os.getenv("BROWSER_NODES"), 0)
logger.info(f"HUB_URL address is {HUB_URL} and have {BROWSER_NODES} browser nodes")


# PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT"))
logger.info(f"PROJECT_ROOT path is: {PROJECT_ROOT}")


DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
LOG_DIR = PROJECT_ROOT / "logs"

SETTINGS_DIR = PROJECT_ROOT / "settings"
FIREFOX_OPTIONS = SETTINGS_DIR / "firefox.yaml"

[
    d.mkdir(exist_ok=True)
    for d in [
        DATA_DIR,
        RAW_DATA_DIR,
        INTERIM_DATA_DIR,
        PROCESSED_DATA_DIR,
        EXTERNAL_DATA_DIR,
        MODELS_DIR,
        REPORTS_DIR,
        FIGURES_DIR,
        LOG_DIR,
        SETTINGS_DIR,
    ]
]


# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
