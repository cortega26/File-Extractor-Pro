"""Configuration management for File Extractor Pro."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Tuple

from constants import DEFAULT_EXCLUDE
from logging_utils import logger


class ConfigValidationError(ValueError):
    """Raised when configuration values fail validation."""


@dataclass(frozen=True)
class AppSettings:
    """Typed configuration schema with validation helpers."""

    output_file: str = "output.txt"
    mode: str = "inclusion"
    include_hidden: bool = False
    exclude_files: Tuple[str, ...] = field(
        default_factory=lambda: tuple(DEFAULT_EXCLUDE)
    )
    exclude_folders: Tuple[str, ...] = field(
        default_factory=lambda: tuple(DEFAULT_EXCLUDE)
    )
    theme: str = "light"
    batch_size: int = 100
    max_memory_mb: int = 512

    _VALID_MODES: Tuple[str, ...] = ("inclusion", "exclusion")
    _VALID_THEMES: Tuple[str, ...] = ("light", "dark")

    @classmethod
    def from_raw(cls, raw: Mapping[str, str]) -> "AppSettings":
        """Create an instance from raw string values."""

        defaults = cls()
        data: Dict[str, Any] = {
            "output_file": defaults.output_file,
            "mode": defaults.mode,
            "include_hidden": defaults.include_hidden,
            "exclude_files": defaults.exclude_files,
            "exclude_folders": defaults.exclude_folders,
            "theme": defaults.theme,
            "batch_size": defaults.batch_size,
            "max_memory_mb": defaults.max_memory_mb,
        }

        for key, value in raw.items():
            if key not in data:
                continue
            data[key] = cls._coerce_value(key, value)

        instance = cls(**data)
        instance._validate()
        return instance

    @staticmethod
    def _coerce_value(key: str, value: str) -> Any:
        """Coerce raw string configuration values into their typed form."""

        if key in {"exclude_files", "exclude_folders"}:
            parts = [part.strip() for part in value.split(",") if part.strip()]
            return tuple(parts)
        if key == "include_hidden":
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
            raise ConfigValidationError(
                "include_hidden must be true/false, yes/no, or 1/0"
            )
        if key in {"batch_size", "max_memory_mb"}:
            try:
                coerced = int(value)
            except ValueError as exc:  # pragma: no cover - defensive guard
                raise ConfigValidationError(f"{key} must be an integer") from exc
            return coerced
        return value.strip()

    def _validate(self) -> None:
        """Validate configuration values and raise if invalid."""

        if not self.output_file:
            raise ConfigValidationError("output_file cannot be empty")
        if self.mode not in self._VALID_MODES:
            raise ConfigValidationError(
                f"mode must be one of {', '.join(self._VALID_MODES)}"
            )
        if self.theme not in self._VALID_THEMES:
            raise ConfigValidationError(
                f"theme must be one of {', '.join(self._VALID_THEMES)}"
            )
        if self.batch_size <= 0:
            raise ConfigValidationError("batch_size must be greater than zero")
        if self.max_memory_mb <= 0:
            raise ConfigValidationError("max_memory_mb must be greater than zero")

    def to_raw_dict(self) -> Dict[str, str]:
        """Serialize settings back to string values for configparser."""

        return {
            "output_file": self.output_file,
            "mode": self.mode,
            "include_hidden": str(self.include_hidden).lower(),
            "exclude_files": ", ".join(self.exclude_files),
            "exclude_folders": ", ".join(self.exclude_folders),
            "theme": self.theme,
            "batch_size": str(self.batch_size),
            "max_memory_mb": str(self.max_memory_mb),
        }


class Config:
    """Configuration manager with improved error handling and validation."""

    def __init__(self, config_file: str = "config.ini"):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.settings: AppSettings = AppSettings()
        self.load()

    def load(self) -> None:
        """Load configuration with error handling."""
        try:
            if os.path.exists(self.config_file):
                self.config.read(self.config_file)
                self._load_settings_from_parser()
            else:
                self._reset_to_defaults()
                logger.info("Created new configuration file: %s", self.config_file)
        except Exception as exc:
            logger.error("Error loading configuration: %s", exc)
            self._reset_to_defaults()

    def _reset_to_defaults(self) -> None:
        """Reset configuration to defaults and persist them."""

        self.settings = AppSettings()
        self.config["DEFAULT"] = self.settings.to_raw_dict()
        self.save()

    def _load_settings_from_parser(self) -> None:
        """Load and validate settings from the underlying parser."""

        try:
            raw_defaults: Mapping[str, str] = dict(self.config["DEFAULT"])
            self.settings = AppSettings.from_raw(raw_defaults)
            # Persist normalized representation in case formatting changed
            self.config["DEFAULT"] = self.settings.to_raw_dict()
            self.save()
        except (ConfigValidationError, KeyError) as exc:
            logger.warning(
                "Invalid configuration detected. Resetting to defaults: %s", exc
            )
            self._reset_to_defaults()

    def save(self) -> None:
        """Save configuration with error handling."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as config_file:
                self.config.write(config_file)
            logger.debug("Configuration saved successfully")
        except Exception as exc:
            logger.error("Error saving configuration: %s", exc)

    def get(self, key: str, fallback: Any = None) -> Any:
        """Get configuration value with type checking."""
        if hasattr(self.settings, key):
            value = getattr(self.settings, key)
            if isinstance(value, tuple):
                return ", ".join(value)
            if isinstance(value, bool):
                return str(value).lower()
            if isinstance(value, int):
                return str(value)
            return value
        return fallback

    def get_typed(self, key: str, fallback: Any = None) -> Any:
        """Retrieve a typed configuration value."""

        return getattr(self.settings, key, fallback)

    def set(self, key: str, value: str) -> None:
        """Set configuration value with validation."""
        try:
            if hasattr(self.settings, key):
                raw_values = self.settings.to_raw_dict()
                raw_values[key] = str(value)
                self.settings = AppSettings.from_raw(raw_values)
                self.config["DEFAULT"] = self.settings.to_raw_dict()
            else:
                self.config.set("DEFAULT", key, str(value))
            self.save()
        except ConfigValidationError as exc:
            logger.error("Invalid value for config key %s: %s", key, exc)
            raise ValueError(f"Invalid value for {key}: {exc}") from exc
        except Exception as exc:  # pragma: no cover - unexpected failure
            logger.error("Error setting config value %s: %s", key, exc)
            raise


__all__ = ["AppSettings", "Config", "ConfigValidationError"]
