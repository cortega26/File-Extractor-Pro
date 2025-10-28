"""Entry point for launching the File Extractor Pro desktop application.

The module coordinates logging configuration, desktop UI initialization,
and enhanced error handling to ensure a resilient experience for end users.
"""

from __future__ import annotations

import platform
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from types import TracebackType

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


def handle_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Log uncaught exceptions and present a user-friendly notification."""

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical(
        "Uncaught exception",
        exc_info=(exc_type, exc_value, exc_traceback),
    )

    error_message = (
        "A critical error has occurred and the application must close.\n\n"
        "Please check the log file for detailed information."
    )

    # Ensure a Tk root exists for displaying the error message.
    created_root = False
    root = tk._default_root  # type: ignore[attr-defined]
    if root is None:
        root = tk.Tk()
        root.withdraw()
        created_root = True

    messagebox.showerror("Critical Error", error_message)

    if created_root:
        root.destroy()

    sys.exit(1)


def configure_dpi_awareness() -> None:
    """Improve display scaling on Windows systems when possible."""

    if platform.system() != "Windows":
        return

    try:
        from ctypes import windll  # type: ignore

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception as exc:  # pragma: no cover - OS specific
        logger.warning("Could not set DPI awareness: %s", exc)


def main() -> None:
    """Main application entry point with improved error handling."""

    root: tk.Tk | None = None
    try:
        if not logger.handlers:
            configure_logging()

        sys.excepthook = handle_uncaught_exception
        logger.info("Starting File Extractor Pro")

        configure_dpi_awareness()

        root = tk.Tk()
        root.title("File Extractor Pro")

        try:
            style = ttk.Style(root)
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError as exc:  # pragma: no cover - UI environment specific
            logger.warning("Unable to apply ttk theme: %s", exc)

        FileExtractorGUI(root)
        root.mainloop()

    except Exception as exc:
        logger.critical("Critical error in main: %s", exc, exc_info=True)
        if root:
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
    "configure_dpi_awareness",
    "FileProcessor",
    "FileExtractorGUI",
    "COMMON_EXTENSIONS",
    "DEFAULT_EXCLUDE",
    "SPECIFICATION_FILES",
    "CHUNK_SIZE",
    "configure_logging",
    "handle_uncaught_exception",
    "logger",
    "main",
]


if __name__ == "__main__":
    main()
