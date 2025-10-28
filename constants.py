"""Shared constants for File Extractor Pro."""

from __future__ import annotations

from typing import List

COMMON_EXTENSIONS: List[str] = [
    ".css",
    ".csv",
    ".db",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".log",
    ".md",
    ".py",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
]

DEFAULT_EXCLUDE: List[str] = [
    ".git",
    ".vscode",
    "__pycache__",
    "venv",
    "node_modules",
    ".venv",
    ".pytest_cache",
]

SPECIFICATION_FILES: List[str] = ["README.md", "SPECIFICATIONS.md"]

CHUNK_SIZE: int = 8192


__all__ = [
    "COMMON_EXTENSIONS",
    "DEFAULT_EXCLUDE",
    "SPECIFICATION_FILES",
    "CHUNK_SIZE",
]
