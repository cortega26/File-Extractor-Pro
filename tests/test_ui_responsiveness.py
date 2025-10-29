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
    assert gui.main_frame.grid_rowconfigure(11)["weight"] >= 1


def test_window_minsize_matches_required_size(tk_root: tk.Tk) -> None:
    from ui import FileExtractorGUI

    FileExtractorGUI(tk_root)
    tk_root.update_idletasks()

    min_width, min_height = tk_root.minsize()
    assert min_width >= tk_root.winfo_reqwidth()
    assert min_height >= tk_root.winfo_reqheight()


def test_cancel_extraction_posts_queue_message(tk_root: tk.Tk) -> None:
    """Cancelling an in-flight extraction should enqueue a status update."""

    from ui import FileExtractorGUI

    gui = FileExtractorGUI(tk_root)
    gui.extraction_in_progress = True
    gui.extract_button.config(state="disabled")
    gui.progress_var.set(50)
    gui.status_var.set("Working")

    gui.service.is_running = lambda: True  # type: ignore[assignment]

    while not gui.output_queue.empty():
        gui.output_queue.get_nowait()

    gui.cancel_extraction()

    assert gui.output_queue.get_nowait() == (
        "info",
        "Extraction cancellation requested",
    )
    assert gui.extract_button["state"] == "normal"
    assert gui.progress_var.get() == 0
    assert gui.status_var.get() == "Ready"
    assert not gui.extraction_in_progress


# Fix: Q-102
def test_prepare_extraction_sets_indeterminate_progress(tk_root: tk.Tk) -> None:
    from ui import FileExtractorGUI

    gui = FileExtractorGUI(tk_root)
    gui.prepare_extraction()

    tk_root.update()
    assert gui.progress_bar.cget("mode") == "indeterminate"
    assert gui._progress_animation_running  # type: ignore[attr-defined]

    gui.reset_extraction_state()
    tk_root.update()
    assert gui.progress_bar.cget("mode") == "determinate"


# Fix: Q-102
def test_update_progress_switches_to_determinate_and_monotonic(
    tk_root: tk.Tk,
) -> None:
    from ui import FileExtractorGUI

    gui = FileExtractorGUI(tk_root)
    gui.prepare_extraction()

    gui.update_progress(0, 5)
    tk_root.update()
    initial_progress = gui.progress_var.get()
    assert gui.progress_bar.cget("mode") == "determinate"

    gui.update_progress(3, 5)
    tk_root.update()
    after_progress = gui.progress_var.get()
    assert after_progress >= initial_progress

    gui.update_progress(2, 5)
    tk_root.update()
    assert gui.progress_var.get() >= after_progress


# Fix: Q-102
def test_update_progress_indeterminate_status_message(tk_root: tk.Tk) -> None:
    from ui import FileExtractorGUI

    gui = FileExtractorGUI(tk_root)
    gui.prepare_extraction()

    gui.update_progress(1, -1)
    tk_root.update()

    assert "estimating total" in gui.status_var.get().lower()


# Fix: Q-102
def test_update_progress_zero_total_prompts_guidance(tk_root: tk.Tk) -> None:
    from ui import FileExtractorGUI

    gui = FileExtractorGUI(tk_root)
    gui.prepare_extraction()

    gui.update_progress(0, 0)
    tk_root.update()

    message = gui.status_var.get()
    assert "no eligible files" in message.lower()
