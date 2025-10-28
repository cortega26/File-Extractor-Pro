"""Tests for responsive layout behavior in the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from tkinter import TclError
from typing import Iterator

import pytest


@pytest.fixture()
def tk_root() -> Iterator[tk.Tk]:
    """Provide a Tk root window for layout tests."""

    try:
        root = tk.Tk()
    except TclError as exc:
        pytest.skip(f"Tk not available: {exc}")
    root.withdraw()
    try:
        yield root
    finally:
        root.destroy()


def test_main_frame_expands_with_window(tk_root: tk.Tk) -> None:
    from ui import FileExtractorGUI

    gui = FileExtractorGUI(tk_root)
    tk_root.update_idletasks()

    assert tk_root.grid_rowconfigure(0)["weight"] == 1
    assert tk_root.grid_columnconfigure(0)["weight"] == 1
    assert gui.main_frame.grid_rowconfigure(10)["weight"] == 1


def test_window_minsize_matches_required_size(tk_root: tk.Tk) -> None:
    from ui import FileExtractorGUI

    FileExtractorGUI(tk_root)
    tk_root.update_idletasks()

    min_width, min_height = tk_root.minsize()
    assert min_width >= tk_root.winfo_reqwidth()
    assert min_height >= tk_root.winfo_reqheight()
