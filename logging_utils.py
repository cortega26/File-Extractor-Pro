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
    target_logger: Optional[logging.Logger] = None,
    replace_handlers: bool = True,
) -> logging.Logger:
    """Configure logging for the supplied logger instance.

    Parameters
    ----------
    level:
        Logging level applied to the logger.
    handler:
        Optional handler to attach. When omitted a ``RotatingFileHandler``
        targeting ``log_file`` is created.
    log_file:
        Path of the log file used when ``handler`` is not provided.
    max_bytes:
        Maximum size of the rotating log file before rollover.
    backup_count:
        Number of rotated log files to retain.
    target_logger:
        The logger instance to configure. Defaults to the module level
        ``file_extractor`` logger which remains unconfigured until this
        function is invoked.
    replace_handlers:
        When ``True`` (default) existing handlers on ``target_logger`` are
        cleared prior to attaching ``handler``.
    """

    configured_logger = target_logger or logger

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

    if replace_handlers:
        configured_logger.handlers.clear()

    configured_logger.addHandler(handler)
    configured_logger.setLevel(level)
    configured_logger.propagate = False
    return configured_logger


__all__ = ["logger", "configure_logging"]
