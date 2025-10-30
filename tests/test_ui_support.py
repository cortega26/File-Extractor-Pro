"""Regression tests for the modularised UI support components."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from types import SimpleNamespace

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


# Fix: Q-103
def test_layout_builders_create_menu_and_status_bar(tk_root: tk.Tk) -> None:
    """Menu/status builders should wire callbacks and styling."""

    from ui_support import build_menu_bar, build_status_bar

    calls = {"exit": 0, "theme": 0}

    menu = build_menu_bar(
        tk_root,
        on_exit=lambda: calls.__setitem__("exit", calls["exit"] + 1),
        on_toggle_theme=lambda: calls.__setitem__("theme", calls["theme"] + 1),
    )

    file_menu = menu.nametowidget(menu.entrycget(0, "menu"))
    options_menu = menu.nametowidget(menu.entrycget(1, "menu"))

    file_menu.invoke(0)
    options_menu.invoke(0)

    assert calls["exit"] == 1
    assert calls["theme"] == 1

    status_var, status_bar = build_status_bar(tk_root)
    assert isinstance(status_var, tk.StringVar)
    assert status_bar.cget("style") == "Status.TLabel"


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

    banner.show_success("Extraction complete", detail="Run summary: processed 3 files")
    assert banner._current_severity == "success"
    assert "complete" in banner._message_var.get().lower()
    assert "run summary" in banner._detail_var.get().lower()


# Fix: ux_accessibility_status_guidance
def test_status_banner_error_populates_default_guidance(tk_root: tk.Tk) -> None:
    """Error messages should include actionable instructions when detail missing."""

    from ui_support import StatusBanner

    banner = StatusBanner(tk_root)
    banner.show_error("Extraction failed")

    assert "review the extraction log" in banner._detail_var.get().lower()

    banner.show_error("Extraction failed", detail="Check folder permissions")
    assert banner._detail_var.get() == "Check folder permissions"


# Fix: Q-103
def test_queue_dispatcher_routes_messages() -> None:
    from ui_support import QueueDispatcher

    class Transcript:
        def __init__(self) -> None:
            self.lines: list[tuple[str, str, str | None]] = []

        def insert(self, index: str, text: str, tag: str | None = None) -> None:
            self.lines.append((index, text, tag))

        def see(self, index: str) -> None:  # pragma: no cover - not used
            self.last_seen = index  # type: ignore[attr-defined]

        def update_idletasks(self) -> None:  # pragma: no cover - not used
            return None

    transcript = Transcript()
    banner_calls: list[tuple[str, object]] = []

    dispatcher = QueueDispatcher(
        transcript=transcript,
        banner_callback=lambda level, payload: banner_calls.append((level, payload)),
        state_callback=lambda payload: banner_calls.append(("state", payload)),
    )

    result = dispatcher.dispatch("warning", "Check filters")

    assert result.wrote_to_transcript
    assert transcript.lines[-1][1].startswith("WARNING: Check filters")
    assert banner_calls[-1] == ("warning", "Check filters")


# Fix: Q-103
def test_queue_dispatcher_handles_state_payload() -> None:
    from ui_support import QueueDispatcher

    transcript = SimpleNamespace(
        lines=[],
        insert=lambda *args, **kwargs: transcript.lines.append(args),  # type: ignore[var-annotated]
        see=lambda *_args, **_kwargs: None,
        update_idletasks=lambda: None,
    )

    states: list[dict[str, object]] = []
    dispatcher = QueueDispatcher(
        transcript=transcript,
        banner_callback=lambda *_args: None,
        state_callback=lambda payload: states.append(payload),
    )

    result = dispatcher.dispatch("state", {"status": "finished"})

    assert not result.wrote_to_transcript
    assert states == [{"status": "finished"}]


# Fix: ux_accessibility_keyboard_hints
def test_shortcut_hint_manager_announces_hints(tk_root: tk.Tk) -> None:
    from ui_support import ShortcutHintManager

    status_var = tk.StringVar(value="Ready")
    button = ttk.Button(tk_root, text="Action")
    button.pack()

    manager = ShortcutHintManager(status_var)
    manager.register_hints([(button, "Alt+A — activate action")])
    manager.set_default_message("Ready")

    button.event_generate("<Enter>")
    assert "Alt+A" in status_var.get()

    button.event_generate("<Leave>")
    assert status_var.get() == "Ready"
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

