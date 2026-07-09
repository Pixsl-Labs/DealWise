from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from dealwise.config import ConfigManager


def setup_logging(config_manager: ConfigManager) -> logging.Logger:
    """Configure application logging.

    Logs are written to the user's config directory rather than the project
    directory so runtime data never pollutes Git.
    """

    logger = logging.getLogger("dealwise")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    log_file = config_manager.logs_dir / "dealwise.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.propagate = False

    logger.info("DealWise logging initialised")
    return logger
