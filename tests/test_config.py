"""Tests for the typed configuration schema and validation logic."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_config_class():
    """Load the ``Config`` class from the application module."""

    module = importlib.import_module("file_extractor")
    return module.Config


def read_raw_config(path: Path) -> str:
    """Utility to read the raw config text for assertions."""

    return path.read_text(encoding="utf-8")


def test_config_creates_file_with_defaults(tmp_path: Path) -> None:
    """Configuration instantiation should create a file with default values."""

    config_path = tmp_path / "config.ini"

    Config = load_config_class()
    config = Config(str(config_path))

    assert config_path.exists()
    assert config.get("mode") == "inclusion"
    assert "output_file = output.txt" in read_raw_config(config_path)


def test_invalid_config_values_reset_to_defaults(tmp_path: Path) -> None:
    """Invalid persisted values should be replaced with defaults on load."""

    config_path = tmp_path / "config.ini"
    config_path.write_text(
        """
[DEFAULT]
mode = invalid
include_hidden = maybe
batch_size = -5
max_memory_mb = 0
""".strip(),
        encoding="utf-8",
    )

    Config = load_config_class()
    config = Config(str(config_path))

    assert config.get("mode") == "inclusion"
    assert config.get("include_hidden") == "false"
    assert config.get("batch_size") == "100"
    assert config.get("max_memory_mb") == "512"


def test_setting_invalid_value_raises_and_preserves_existing(tmp_path: Path) -> None:
    """Setting an invalid value should raise and keep previous valid settings."""

    config_path = tmp_path / "config.ini"
    Config = load_config_class()
    config = Config(str(config_path))

    with pytest.raises(ValueError):
        config.set("mode", "invalid")

    assert config.get("mode") == "inclusion"


def test_recent_folders_round_trip(tmp_path: Path) -> None:
    """Updating recent folders should persist and remove duplicates."""

    config_path = tmp_path / "config.ini"
    Config = load_config_class()
    config = Config(str(config_path))

    config.update_recent_folders(str(tmp_path / "first"))
    config.update_recent_folders(str(tmp_path / "second"))
    config.update_recent_folders(str(tmp_path / "first"))

    recent = config.get_recent_folders()
    assert recent[0].endswith("first")
    assert recent[1].endswith("second")

    raw = json.loads(config.config["DEFAULT"]["recent_folders"])
    assert isinstance(raw, list)
    assert len(raw) == 2


def test_recent_folders_limit(tmp_path: Path) -> None:
    """Recent folders history should respect the configured limit."""

    config_path = tmp_path / "config.ini"
    Config = load_config_class()
    config = Config(str(config_path))

    for index in range(8):
        config.update_recent_folders(str(tmp_path / f"folder_{index}"), limit=3)

    recent = config.get_recent_folders()
    assert len(recent) == 3
    assert recent[0].endswith("folder_7")
    assert recent[-1].endswith("folder_5")
