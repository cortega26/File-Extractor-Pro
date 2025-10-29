from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Sequence, cast

import tkinter as tk

from ui import FileExtractorGUI


class DummyButton:
    def __init__(self) -> None:
        self.state = "disabled"
        self.focused = False

    def config(self, **kwargs) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.state = state

    def __getitem__(self, item: str) -> str:
        if item == "state":
            return self.state
        raise KeyError(item)

    def focus_set(self) -> None:
        self.focused = True


class DummyVar:
    def __init__(self, value: str | float = "") -> None:
        self.value = value

    def set(self, value: str | float) -> None:
        self.value = value

    def get(self) -> str | float:
        return self.value


class DummyText:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def insert(self, _index: object, message: str, _tag: object | None = None) -> None:
        self.lines.append(message)

    def see(self, *_args: object, **_kwargs: object) -> None:
        return None

    def update_idletasks(self) -> None:
        return None


class _DummyDispatchResult:
    def __init__(self, wrote: bool) -> None:
        self.wrote_to_transcript = wrote


class _QueueDispatcherStub:
    def __init__(self, should_write: bool = False) -> None:
        self.records: list[tuple[str, object]] = []
        self._should_write = should_write

    def dispatch(self, level: str, payload: object) -> _DummyDispatchResult:
        self.records.append((level, payload))
        return _DummyDispatchResult(self._should_write)


class _StatusBannerStub:
    """Record status banner messages for assertions."""

    def __init__(self) -> None:
        self.messages: dict[str, str] = {}
        self.details: dict[str, str | None] = {}

    def show_success(self, message: str, *, detail: str | None = None) -> None:
        self.messages["success"] = message
        self.details["success"] = detail

    def show_error(self, message: str, *, detail: str | None = None) -> None:
        self.messages["error"] = message
        self.details["error"] = detail

    def show_warning(self, message: str, *, detail: str | None = None) -> None:
        self.messages["warning"] = message
        self.details["warning"] = detail

    def show(
        self, message: str, *, severity: str = "info", detail: str | None = None
    ) -> None:
        self.messages[severity] = message
        self.details[severity] = detail

    def clear(self) -> None:
        self.messages.clear()
        self.details.clear()

    def apply_palette(self, _palette: Any) -> None:
        return None


def _make_gui_stub() -> FileExtractorGUI:
    gui = cast(FileExtractorGUI, object.__new__(FileExtractorGUI))
    gui.extract_button = cast(Any, DummyButton())
    gui.status_var = cast(Any, DummyVar())
    gui.progress_var = cast(Any, DummyVar(0.0))
    gui.progress_bar = cast(
        Any,
        SimpleNamespace(
            cget=lambda *_args: "determinate",
            stop=lambda: None,
            configure=lambda **_kwargs: None,
        ),
    )
    gui.status_banner = _StatusBannerStub()
    gui.extraction_in_progress = True
    gui._progress_animation_running = False  # type: ignore[attr-defined]
    gui._last_progress_value = 0.0  # type: ignore[attr-defined]
    gui._pending_status_message = None  # type: ignore[attr-defined]
    gui._pending_status_detail = None  # type: ignore[attr-defined]
    gui._pending_status_severity = "info"  # type: ignore[attr-defined]
    gui.service = SimpleNamespace(cancel=lambda: None)
    gui.output_text = cast(Any, DummyText())
    gui.queue_dispatcher = _QueueDispatcherStub()
    gui.shortcut_hint_manager = SimpleNamespace(
        set_default_message=lambda *_args, **_kwargs: None,
        register_hints=lambda *_args, **_kwargs: None,
    )
    gui.output_file_name = cast(Any, DummyVar("extraction.txt"))
    return gui


def test_handle_service_state_success_sets_ready_state() -> None:
    gui = _make_gui_stub()

    FileExtractorGUI._handle_service_state(
        gui, {"status": "finished", "result": "success"}
    )

    assert not gui.extraction_in_progress
    assert gui.extract_button["state"] == "normal"
    assert gui._pending_status_message == "Extraction complete"  # type: ignore[attr-defined]

    FileExtractorGUI.reset_extraction_state(gui)

    assert gui.status_var.get() == "Extraction complete"
    assert gui.extract_button["state"] == "normal"
    assert gui._pending_status_message is None  # type: ignore[attr-defined]
    assert gui.progress_var.get() == 0.0
    assert gui.extract_button.focused


def test_handle_service_state_error_sets_failure_message() -> None:
    gui = _make_gui_stub()

    FileExtractorGUI._handle_service_state(
        gui,
        {
            "status": "finished",
            "result": "error",
            "message": "boom",
        },
    )

    expected = (
        "Extraction failed: boom. Review the log output for troubleshooting details."
    )
    assert gui._pending_status_message == expected  # type: ignore[attr-defined]
    assert gui.status_banner.messages["error"] == expected  # type: ignore[attr-defined]


# Fix: ux_accessibility_status_guidance
def test_handle_service_state_success_with_no_matches_prompts_user() -> None:
    gui = _make_gui_stub()

    FileExtractorGUI._handle_service_state(
        gui,
        {
            "status": "finished",
            "result": "success",
            "metrics": {
                "processed_files": 0,
                "skipped_files": 0,
            },
        },
    )

    message = gui._pending_status_message  # type: ignore[attr-defined]
    assert message is not None
    assert "no files matched" in message.lower()
    assert gui.status_banner.messages["warning"] == message  # type: ignore[attr-defined]
    FileExtractorGUI.reset_extraction_state(gui)
    assert "no files matched" in gui.status_var.get().lower()


# Fix: Q-108
def test_handle_service_state_with_metrics_records_summary() -> None:
    gui = _make_gui_stub()

    FileExtractorGUI._handle_service_state(
        gui,
        {
            "status": "finished",
            "result": "success",
            "metrics": {
                "processed_files": 5,
                "total_files": 5,
                "elapsed_seconds": 1.5,
                "files_per_second": 3.3,
                "max_queue_depth": 4,
                "dropped_messages": 0,
                "skipped_files": 1,
            },
        },
    )

    detail = gui.status_banner.details["success"]  # type: ignore[attr-defined]
    assert detail is not None
    assert "Run summary" in detail
    assert gui.output_text.lines  # type: ignore[attr-defined]
    assert gui.output_text.lines[-1].startswith("Run summary")  # type: ignore[attr-defined]
    assert gui._pending_status_detail == detail  # type: ignore[attr-defined]
    assert gui._pending_status_severity == "success"  # type: ignore[attr-defined]


# Fix: Q-107
def test_register_keyboard_shortcuts_announces_accelerators() -> None:
    class RecordingKeyboardManager:
        def __init__(self) -> None:
            self.bindings: dict[str, object] = {}

        def register_shortcuts(
            self, shortcuts: dict[str, Callable[[tk.Event], str]]
        ) -> None:
            self.bindings.update(shortcuts)

        def configure_focus_ring(
            self,
            *,
            preferred_order: Sequence[tk.Widget],
            skip: Sequence[tk.Widget] = (),
        ) -> None:
            pass

    gui = cast(FileExtractorGUI, object.__new__(FileExtractorGUI))
    gui.keyboard_manager = RecordingKeyboardManager()  # type: ignore[attr-defined]
    setattr(gui, "execute", lambda: None)
    setattr(gui, "cancel_extraction", lambda: None)
    setattr(gui, "generate_report", lambda: None)
    gui.status_var = cast(Any, DummyVar(""))
    gui.extraction_in_progress = False

    FileExtractorGUI._register_keyboard_shortcuts(gui)

    sequences = set(gui.keyboard_manager.bindings)  # type: ignore[attr-defined]
    assert {"<Alt-e>", "<Alt-c>", "<Alt-g>"}.issubset(sequences)
    assert gui.status_var.get().startswith("Shortcuts: Alt+E")


def test_gather_selected_extensions_normalises_tokens() -> None:
    gui = cast(FileExtractorGUI, object.__new__(FileExtractorGUI))
    gui.extension_vars = {
        ".txt": SimpleNamespace(get=lambda: True),
        "PY": SimpleNamespace(get=lambda: False),
    }
    gui.custom_extensions = SimpleNamespace(get=lambda: "*.MD, data")

    result = FileExtractorGUI._gather_selected_extensions(gui)

    assert result == (".txt", ".md", ".data")
