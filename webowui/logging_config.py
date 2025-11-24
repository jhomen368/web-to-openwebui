"""
Simple file + console logging with rotation.
"""

import logging
import logging.handlers
from pathlib import Path

from rich.logging import RichHandler


def setup_logging(logs_dir: Path, log_level: str = "INFO"):
    """
    Configure file and console logging with automatic rotation.

    Args:
        logs_dir: Directory for log files (data/logs/)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers.clear()

    # Console output (Rich formatting)
    console_handler = RichHandler(rich_tracebacks=True)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)

    # File output with rotation (midnight, keep 14 days)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        logs_dir / "app.log", when="midnight", interval=1, backupCount=14, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    root_logger.addHandler(file_handler)

    logging.info(f"✓ Logging configured: {logs_dir}/app.log (14-day rotation)")
