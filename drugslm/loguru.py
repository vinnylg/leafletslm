import logging
from pathlib import Path
import sys
from typing import Optional

from loguru import logger

_configured = False


class InterceptHandler(logging.Handler):
    """
    Custom handler to intercept standard 'logging' records
    and redirect them to 'loguru'.
    """

    def emit(self, record):
        # Tries to find the correct log level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the stack frame that originated the log
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # If frame is None (rare), use default depth
        if frame is None:
            depth = 2

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_file_path: Optional[str] = None) -> logger:
    """
    Main function to configure logs.
    Call this at the beginning of EACH entry point (e.g., __main__, dagster op).

    Args:
        log_file_path (Optional[str]): If provided, enables file logging
            to this specific path. If None, only logs to stderr.

    Returns:
        The configured loguru logger instance.
    """
    global _configured
    if _configured:
        return logger  # Return already configured logger

    # 1. Remove the default handler to start fresh
    logger.remove()

    # 2. Add console handler (Always active)
    #    (For Dagster, Docker, etc., which read stdout/stderr)
    logger.add(
        sys.stderr,
        level="INFO",
        format="{time:HH:mm:ss} | {level:<8} | {name}:{function}:{line} - {message}",
        colorize=True,
    )

    # 3. Add file handler (ONLY if a path is provided)
    if log_file_path:
        log_path = Path(log_file_path)
        # Ensure the log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            level="DEBUG",  # Log EVERYTHING (DEBUG and up) to the file
            rotation="10 MB",
            retention="1 week",
            format="{time} | {level:<8} | {name:<25} | {function:<20} | {message}",
            encoding="utf-8",
        )
        logger.info(f"File logging configured at: {log_path.resolve()}")
    else:
        logger.info("File logging disabled (no path provided). Logging to console only.")

    # 4. Intercept standard 'logging' (for libraries)
    logging.root.handlers = []
    logging.root.addHandler(InterceptHandler())
    logging.root.setLevel(logging.DEBUG)

    _configured = True
    logger.info("Logging setup complete. Standard 'logging' is now intercepted.")

    return logger
