"""Regression tests for the modularised UI support components."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import pytest


@pytest.fixture(name="tk_root")
def fixture_tk_root() -> tk.Tk:
    """Create a Tk root for widget tests and ensure cleanup."""

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk not available: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def _build_theme_manager(root: tk.Tk):
    from ui_support import ThemeManager, ThemeTargets

    style = ttk.Style(root)
    main_frame = ttk.Frame(root)
    extensions_frame = ttk.Frame(root)
    status_bar = ttk.Label(root)
    output_text = tk.Text(root)
    manager = ThemeManager(
        style,
        ThemeTargets(
            master=root,
            main_frame=main_frame,
            extensions_frame=extensions_frame,
            status_bar=status_bar,
            output_text=output_text,
        ),
    )
    return manager, main_frame, extensions_frame, status_bar, output_text


# Fix: Q-103
def test_theme_manager_applies_styles(tk_root: tk.Tk) -> None:
    """Applying a theme should configure widget styles consistently."""

    manager, main_frame, extensions_frame, status_bar, _ = _build_theme_manager(tk_root)

    manager.apply("light")
    palette = manager.active_palette()

    assert palette.window_bg.startswith("#")
    assert status_bar.cget("style") == "Status.TLabel"
    assert main_frame.cget("style") == "Main.TFrame"
    assert extensions_frame.cget("style") == "Main.TFrame"


# Fix: ux_accessibility_status_banner
def test_status_banner_respects_severity_styles(tk_root: tk.Tk) -> None:
    """Status banner should track severity and message text."""

    from ui_support import StatusBanner

    banner = StatusBanner(tk_root)
    manager, *_ = _build_theme_manager(tk_root)
    manager.apply("dark")
    banner.apply_palette(manager.active_palette())

    banner.show_error("Extraction failed")
    assert banner._current_severity == "error"
    assert banner._message_var.get() == "Extraction failed"

    banner.show_success("Extraction complete")
    assert banner._current_severity == "success"
    assert "complete" in banner._message_var.get().lower()


# Fix: Q-107
def test_keyboard_manager_configures_focus_and_shortcuts(tk_root: tk.Tk) -> None:
    from ui_support import KeyboardManager

    entry = ttk.Entry(tk_root)
    button = ttk.Button(tk_root)
    label = ttk.Label(tk_root)

    manager = KeyboardManager(tk_root)

    recorded: dict[str, object] = {}

    def handler(event: tk.Event) -> str:  # type: ignore[valid-type]
        recorded["triggered"] = True
        return "break"

    manager.register_shortcuts({"<Alt-e>": handler})
    manager.configure_focus_ring(preferred_order=[entry, button], skip=[label])

    assert entry.cget("takefocus") == "1"
    assert button.cget("takefocus") == "1"
    assert label.cget("takefocus") == "0"

    entry.event_generate("<Alt-e>")
    assert "triggered" in recorded

