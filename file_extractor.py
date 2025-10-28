"""Public interface for File Extractor Pro."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from config_manager import AppSettings, Config, ConfigValidationError
from constants import (
    CHUNK_SIZE,
    COMMON_EXTENSIONS,
    DEFAULT_EXCLUDE,
    SPECIFICATION_FILES,
)
from logging_utils import configure_logging, logger
from processor import FileProcessor
from ui import FileExtractorGUI


def main() -> None:
    """Main application entry point with improved error handling."""

    try:
        if not logger.handlers:
            configure_logging()

        logger.info("Starting File Extractor Pro")

        root = tk.Tk()
        root.title("File Extractor Pro")

        try:
            from ctypes import windll  # type: ignore

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        app = FileExtractorGUI(root)
        root.mainloop()

    except Exception as exc:
        logger.critical("Critical error in main: %s", exc, exc_info=True)
        if "root" in locals() and root:
            messagebox.showerror(
                "Critical Error",
                f"A critical error has occurred: {exc}\n\nPlease check the log file.",
            )
            root.destroy()
        raise


__all__ = [
    "AppSettings",
    "Config",
    "ConfigValidationError",
    "FileProcessor",
    "FileExtractorGUI",
    "COMMON_EXTENSIONS",
    "DEFAULT_EXCLUDE",
    "SPECIFICATION_FILES",
    "CHUNK_SIZE",
    "configure_logging",
    "logger",
    "main",
]


if __name__ == "__main__":
    main()
