"""Tests for logging configuration behavior."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Iterator

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture()
def fresh_module() -> Iterator[object]:
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


def test_import_does_not_configure_handlers(fresh_module: object) -> None:
    module = fresh_module
    logger = getattr(module, "logger")
    assert list(logger.handlers) == []
    assert logger.propagate is True


def test_configure_logging_allows_injection(fresh_module: object) -> None:
    module = fresh_module
    handler = logging.StreamHandler()

    configured_logger = module.configure_logging(level=logging.DEBUG, handler=handler)

    assert configured_logger is module.logger
    assert list(module.logger.handlers) == [handler]
    assert module.logger.level == logging.DEBUG
    assert module.logger.propagate is False
