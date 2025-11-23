from datetime import datetime
import logging
import logging.handlers
from pathlib import Path
import sys
from typing import Optional, Union

from drugslm.config import EXECUTION_ID, LOG_DIR, PROJECT_ROOT

# Try to import tqdm to use its thread-safe write method
try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# Global flag to prevent double configuration during imports/re-runs
_configured = False


class TqdmLoggingHandler(logging.Handler):
    """
    A custom logging handler that uses tqdm.write() to ensure logs
    print above the progress bar without breaking visual layout.
    """

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            # tqdm.write prints safely above the progress bar
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(log_file_path: Optional[Union[str, Path]] = None) -> logging.Logger:
    """
    Configures the standard Python logging module.

    This function sets up the root logger with:
    1. A Console Handler (stderr) for INFO level and above.
    2. An optional Rotating File Handler for DEBUG level and above.

    Call this at the beginning of EACH entry point.

    Args:
        log_file_path (Optional[Union[str, Path]]): If provided, enables file logging
            to this path with rotation (10MB limit, 5 backups).
            If None, only logs to stderr.

    Returns:
        logging.Logger: The configured root logger instance.
    """
    global _configured
    if _configured:
        return logging.getLogger()

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, filter at handlers

    # Remove default/existing handlers to prevent duplication or conflicts
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # --- Formatters ---
    # Console: Concise, colored (if supported by terminal), time-focused
    console_fmt = logging.Formatter(
        fmt="{asctime} | {levelname:<8} | {name}:{funcName}:{lineno} - {message}",
        datefmt="%H:%M:%S",
        style="{",
    )

    # File: Detailed, date-focused, structured alignment
    file_fmt = logging.Formatter(
        fmt="{asctime} | {levelname:<8} | {name:<25} | {funcName:<20} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    # --- 1. Console Handler (Stderr) ---
    # Checks if tqdm is available to prevent progress bar breakage
    if HAS_TQDM:
        console_handler = TqdmLoggingHandler()
    else:
        console_handler = logging.StreamHandler(sys.stderr)

    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)
    root_logger.addHandler(console_handler)

    # --- 2. File Handler (Optional) ---
    if log_file_path:
        log_path = Path(log_file_path)

        # Ensure directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # RotatingFileHandler: Keeps 5 files of 10MB each
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            # maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)
        root_logger.addHandler(file_handler)

        logging.info(f"File logging configured at: {log_path.resolve()}")
    else:
        logging.info("File logging disabled. Logging to console only.")

    _configured = True
    return root_logger


def get_log_path(script_file: Union[str, Path], timestamp: str = EXECUTION_ID) -> Path:
    """
    Generates a log file path mirroring the script's structure within the logs directory.

    This is a pure function and does not create directories on disk.

    Args:
        script_file (Union[str, Path]): The path to the script (usually passed as __file__).

    Returns:
        Path: A Path object representing the target log file location.
    """
    script_path = Path(script_file).resolve()

    try:
        # Try to find the path relative to the project root
        relative_path = script_path.relative_to(PROJECT_ROOT)
    except ValueError:
        # Fallback if script is outside project root
        relative_path = Path(script_path.name)

    # Mirror structure: logs / path / to / script_name / timestamp.log
    # Using parent / stem ensures "my_script.py" becomes a folder "my_script"
    log_subdir_structure = relative_path.parent / relative_path.stem

    return LOG_DIR / log_subdir_structure / f"{timestamp}.log"
