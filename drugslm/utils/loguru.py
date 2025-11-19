from datetime import datetime
import logging
from pathlib import Path
import sys
from typing import Optional, Union

from loguru import logger

from drugslm.config import LOG_DIR, PROJECT_ROOT

# Global flag to prevent double configuration during imports/re-runs
_configured = False


class InterceptHandler(logging.Handler):
    """
    Custom handler to intercept standard 'logging' records
    and redirect them to 'loguru'.
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from stack to correct line number attribution
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_file_path: Optional[Union[str, Path]] = None):
    """
    Main function to configure logs.
    Call this at the beginning of EACH entry point.

    Args:
        log_file_path: If provided, enables file logging to this path.
                       If None, only logs to stderr.
    Returns:
        The configured loguru logger instance.
    """
    global _configured
    if _configured:
        return logger

    # 1. Remove default handler
    logger.remove()

    # 2. Add console handler (Always active)
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}",
        colorize=True,
    )

    # 3. Add file handler (if path provided)
    if log_file_path:
        log_path = Path(log_file_path)

        # Robust directory creation handles the side effect here
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            level="DEBUG",
            rotation="10 MB",
            retention="1 week",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name:<25} | {function:<20} | {message}",
            encoding="utf-8",
        )
        logger.info(f"File logging configured at: {log_path.resolve()}")
    else:
        logger.info("File logging disabled (no path provided). Logging to console only.")

    # 4. Intercept standard 'logging'
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(logging.DEBUG)

    _configured = True
    logger.info("Logging setup complete. Standard 'logging' is now intercepted.")

    return logger


def get_log_path(script_file: Union[str, Path]) -> Path:
    """
    Generates a log file path mirroring the script's structure within the logs directory.
    Pure function: Does not create directories on disk.

    Args:
        script_file: The path to the script (usually passed as __file__).

    Returns:
        A Path object for the log file.
    """
    script_path = Path(script_file).resolve()

    try:
        relative_path = script_path.relative_to(PROJECT_ROOT)
    except ValueError:
        relative_path = Path(script_path.name)

    # Mirror structure: logs / path / to / script_name / timestamp.log
    # Using parent / stem ensures "my_script.py" becomes a folder "my_script"
    log_subdir_structure = relative_path.parent / relative_path.stem

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return LOG_DIR / log_subdir_structure / f"{timestamp}.log"
