"""Logging utilities for File Extractor Pro."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

logger = logging.getLogger("file_extractor")


def configure_logging(
    *,
    level: int = logging.INFO,
    handler: Optional[logging.Handler] = None,
    log_file: str = "file_extractor.log",
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configure application logging for the current process."""

    if handler is None:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s"
    )
    handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


__all__ = ["logger", "configure_logging"]
