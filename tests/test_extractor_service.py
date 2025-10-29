"""Unit tests for the extractor service layer."""

from __future__ import annotations

import threading
import time
from queue import Queue

import pytest

from processor import ExtractionCancelled
from services.extractor_service import ExtractionRequest, ExtractorService


class DummyFileProcessor:
    """Test double that records whether extraction was invoked."""

    def __init__(self, output_queue: Queue) -> None:
        self.output_queue = output_queue
        self.called = threading.Event()

    def extract_files(self, *args, progress_callback, **kwargs):  # type: ignore[override]
        progress_callback(1, 1)
        self.called.set()


def test_start_extraction_runs_worker(tmp_path):
    progress_called = threading.Event()

    def progress_callback(processed: int, total: int) -> None:
        progress_called.set()

    service = ExtractorService(
        file_processor_factory=DummyFileProcessor,
        output_queue=Queue(maxsize=4),
    )

    request = ExtractionRequest(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(),
        exclude_files=(),
        exclude_folders=(),
        output_file_name=str(tmp_path / "out.txt"),
    )

    thread = service.start_extraction(
        request=request,
        progress_callback=progress_callback,
    )
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert not service.is_running()
    assert service.file_processor.called.is_set()
    assert progress_called.is_set()

    state_messages = []
    while not service.output_queue.empty():
        message_type, payload = service.output_queue.get_nowait()
        if message_type == "state":
            state_messages.append(payload)

    assert state_messages
    assert state_messages[-1]["status"] == "finished"
    assert state_messages[-1]["result"] == "success"


def test_start_extraction_raises_when_running(tmp_path):
    barrier = threading.Event()

    class BlockingFileProcessor(DummyFileProcessor):
        def extract_files(self, *args, progress_callback, **kwargs):  # type: ignore[override]
            progress_callback(0, 0)
            barrier.wait()

    def noop_progress(*_args):
        return None

    service = ExtractorService(file_processor_factory=BlockingFileProcessor)
    request = ExtractionRequest(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(),
        exclude_files=(),
        exclude_folders=(),
        output_file_name=str(tmp_path / "out.txt"),
    )

    service.start_extraction(
        request=request,
        progress_callback=noop_progress,
    )

    with pytest.raises(RuntimeError):
        service.start_extraction(
            request=request,
            progress_callback=noop_progress,
        )

    barrier.set()


def test_cancel_extraction_emits_cancel_state(tmp_path):
    proceed = threading.Event()

    class CancellableProcessor(DummyFileProcessor):
        def extract_files(self, *args, progress_callback, is_cancelled, **kwargs):  # type: ignore[override]
            progress_callback(0, 0)
            proceed.set()
            while not is_cancelled():
                time.sleep(0.01)
            raise ExtractionCancelled("cancelled")

    def noop_progress(*_args):
        return None

    service = ExtractorService(
        file_processor_factory=CancellableProcessor,
        output_queue=Queue(maxsize=4),
    )

    request = ExtractionRequest(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(),
        exclude_files=(),
        exclude_folders=(),
        output_file_name=str(tmp_path / "out.txt"),
    )

    thread = service.start_extraction(
        request=request,
        progress_callback=noop_progress,
    )

    proceed.wait(timeout=1)
    service.cancel()
    thread.join(timeout=2)

    assert not service.is_running()

    state_payloads = []
    info_messages = []
    while not service.output_queue.empty():
        kind, payload = service.output_queue.get_nowait()
        if kind == "state":
            state_payloads.append(payload)
        elif kind == "info":
            info_messages.append(payload)

    assert any("cancellation requested" in message for message in info_messages)
    assert any("Extraction cancelled" == message for message in info_messages)
    assert state_payloads
    assert state_payloads[-1]["result"] == "cancelled"


def test_publish_state_update_preserves_state_on_full_queue():
    """State update must be enqueued even when the queue is saturated."""

    output_queue: Queue[tuple[str, object]] = Queue(maxsize=2)
    service = ExtractorService(output_queue=output_queue)

    output_queue.put(("info", "first"))
    output_queue.put(("info", "second"))

    service._publish_state_update({"status": "finished", "result": "success"})

    messages: list[tuple[str, object]] = []
    while not output_queue.empty():
        messages.append(output_queue.get_nowait())

    assert any(level == "state" for level, _ in messages)
    assert len(messages) == 2


def test_publish_state_update_replaces_old_state_when_only_states_present():
    """Newest state update should displace the oldest state entry if required."""

    output_queue: Queue[tuple[str, object]] = Queue(maxsize=2)
    service = ExtractorService(output_queue=output_queue)

    output_queue.put(("state", {"result": "pending"}))
    output_queue.put(("state", {"result": "running"}))

    service._publish_state_update({"status": "finished", "result": "success"})

    results: list[str] = []
    while not output_queue.empty():
        level, payload = output_queue.get_nowait()
        if level == "state" and isinstance(payload, dict):
            results.append(str(payload.get("result")))

    assert "success" in results
    assert len(results) <= 2
