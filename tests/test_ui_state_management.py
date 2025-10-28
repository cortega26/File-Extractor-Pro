from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from ui import FileExtractorGUI


class DummyButton:
    def __init__(self) -> None:
        self.state = "disabled"

    def config(self, **kwargs) -> None:
        state = kwargs.get("state")
        if state is not None:
            self.state = state

    def __getitem__(self, item: str) -> str:
        if item == "state":
            return self.state
        raise KeyError(item)


class DummyVar:
    def __init__(self, value: str | float = "") -> None:
        self.value = value

    def set(self, value: str | float) -> None:
        self.value = value

    def get(self) -> str | float:
        return self.value


def _make_gui_stub() -> FileExtractorGUI:
    gui = cast(FileExtractorGUI, object.__new__(FileExtractorGUI))
    gui.extract_button = cast(Any, DummyButton())
    gui.status_var = cast(Any, DummyVar())
    gui.progress_var = cast(Any, DummyVar(0.0))
    gui.extraction_in_progress = True
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

    assert gui._pending_status_message == "Extraction failed: boom"  # type: ignore[attr-defined]
    FileExtractorGUI.reset_extraction_state(gui)
    assert gui.status_var.get() == "Extraction failed: boom"
