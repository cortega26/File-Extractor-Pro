"""Tests for logging configuration behavior."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterator

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def fresh_module() -> Iterator[ModuleType]:
    """Provide a freshly imported ``file_extractor`` module for each test."""

    module_name = "file_extractor"
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    try:
        yield module
    finally:
        # Ensure module can be reloaded cleanly in subsequent tests
        if hasattr(module, "logger"):
            module.logger.handlers.clear()
        sys.modules.pop(module_name, None)


def test_import_does_not_configure_handlers(fresh_module: ModuleType) -> None:
    module = fresh_module
    logger = getattr(module, "logger")
    assert list(logger.handlers) == []
    assert logger.propagate is True


def test_configure_logging_allows_injection(fresh_module: ModuleType) -> None:
    module = fresh_module
    handler = logging.StreamHandler()

    configured_logger = module.configure_logging(
        level=logging.DEBUG,
        handler=handler,
    )

    assert configured_logger is module.logger
    assert list(module.logger.handlers) == [handler]
    assert module.logger.level == logging.DEBUG
    assert module.logger.propagate is False

    module.logger.handlers.clear()


def test_configure_logging_supports_custom_logger(fresh_module: ModuleType) -> None:
    module = fresh_module
    handler = logging.StreamHandler()
    custom_logger = logging.getLogger("custom")
    existing_handler = logging.NullHandler()
    custom_logger.addHandler(existing_handler)

    configured_logger = module.configure_logging(
        target_logger=custom_logger,
        handler=handler,
    )

    assert configured_logger is custom_logger
    assert list(custom_logger.handlers) == [handler]
    assert custom_logger.propagate is False

    custom_logger.handlers.clear()


def test_configure_logging_appends_when_requested(fresh_module: ModuleType) -> None:
    module = fresh_module
    custom_logger = logging.getLogger("append")
    retained_handler = logging.NullHandler()
    custom_logger.addHandler(retained_handler)

    module.configure_logging(
        target_logger=custom_logger,
        handler=logging.StreamHandler(),
        replace_handlers=False,
    )

    handlers = list(custom_logger.handlers)
    assert retained_handler in handlers
    assert len(handlers) == 2

    custom_logger.handlers.clear()
