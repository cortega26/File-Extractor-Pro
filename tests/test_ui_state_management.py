from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

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


class _StatusBannerStub:
    """Record status banner messages for assertions."""

    def __init__(self) -> None:
        self.messages: dict[str, str] = {}

    def show_success(self, message: str) -> None:
        self.messages["success"] = message

    def show_error(self, message: str) -> None:
        self.messages["error"] = message

    def show_warning(self, message: str) -> None:
        self.messages["warning"] = message

    def show(self, message: str, *, severity: str = "info") -> None:
        self.messages[severity] = message

    def clear(self) -> None:
        self.messages.clear()

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
    gui.service = SimpleNamespace(cancel=lambda: None)
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


# Fix: Q-107
def test_register_keyboard_shortcuts_announces_accelerators() -> None:
    class RecordingMaster:
        def __init__(self) -> None:
            self.bindings: list[tuple[str, object, str | None]] = []

        def bind_all(
            self, sequence: str, callback: object, add: str | None = None
        ) -> None:
            self.bindings.append((sequence, callback, add))

    gui = cast(FileExtractorGUI, object.__new__(FileExtractorGUI))
    gui.master = RecordingMaster()
    setattr(gui, "execute", lambda: None)
    setattr(gui, "cancel_extraction", lambda: None)
    setattr(gui, "generate_report", lambda: None)
    gui._accelerator_callbacks = []  # type: ignore[attr-defined]
    gui.status_var = cast(Any, DummyVar(""))
    gui.extraction_in_progress = False

    FileExtractorGUI._register_keyboard_shortcuts(gui)

    sequences = {seq for seq, _cb, _add in gui.master.bindings}
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
