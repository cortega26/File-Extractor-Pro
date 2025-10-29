"""Unit tests for the extractor service layer."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from queue import Full, Queue

import pytest

from constants import COMMON_EXTENSIONS, DEFAULT_EXCLUDE
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


class RecordingExtensionsProcessor(DummyFileProcessor):
    """Capture the extensions passed into extract_files for assertions."""

    def __init__(self, output_queue: Queue) -> None:
        super().__init__(output_queue)
        self.seen_extensions: tuple[str, ...] | None = None

    def extract_files(self, *args, progress_callback, **kwargs):  # type: ignore[override]
        if len(args) >= 4:
            extensions_arg = args[3]
            if isinstance(extensions_arg, tuple):
                self.seen_extensions = extensions_arg
            else:
                self.seen_extensions = tuple(extensions_arg)
        super().extract_files(*args, progress_callback=progress_callback, **kwargs)


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


def test_start_extraction_defaults_common_extensions_when_inclusion(tmp_path):
    progress_called = threading.Event()

    def progress_callback(processed: int, total: int) -> None:
        progress_called.set()

    service = ExtractorService(
        file_processor_factory=RecordingExtensionsProcessor,
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
    assert progress_called.is_set()
    assert service.file_processor.seen_extensions == tuple(COMMON_EXTENSIONS)


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


# Fix: Q-106
def test_publish_state_update_tracks_latest_payload_on_drop() -> None:
    """Latest state payload should remain accessible even if enqueueing fails."""

    class SaturatedQueue(Queue):
        def put_nowait(self, item):  # type: ignore[override]
            raise Full

    output_queue: Queue[tuple[str, object]] = SaturatedQueue()
    service = ExtractorService(output_queue=output_queue)

    payload = {"status": "finished", "result": "success"}
    service._publish_state_update(payload)

    assert service.get_last_state_payload() == payload


# Fix: Q-108
def test_get_last_run_metrics_returns_processor_snapshot(tmp_path: Path) -> None:
    """Services should expose processor instrumentation data."""

    output_queue: Queue[tuple[str, object]] = Queue()
    service = ExtractorService(output_queue=output_queue)

    data_file = tmp_path / "metric.txt"
    data_file.write_text("payload", encoding="utf-8")

    processor = service.file_processor
    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(".txt",),
        exclude_files=tuple(DEFAULT_EXCLUDE),
        exclude_folders=tuple(DEFAULT_EXCLUDE),
        output_file_name=str(tmp_path / "out.txt"),
    )

    metrics = service.get_last_run_metrics()
    assert metrics is not None
    assert metrics["processed_files"] >= 1
    assert "completed_at" in metrics
    assert "service_dropped_messages" in metrics


# Fix: Q-108
def test_state_payload_includes_metrics(tmp_path: Path) -> None:
    """State updates should include instrumentation metrics for observers."""

    output_queue: Queue[tuple[str, object]] = Queue(maxsize=4)

    class MetricsProcessor(DummyFileProcessor):
        def __init__(self, queue_obj: Queue) -> None:
            super().__init__(queue_obj)
            self.last_run_metrics = {
                "processed_files": 3,
                "total_files": 3,
                "elapsed_seconds": 1.0,
                "files_per_second": 3.0,
                "max_queue_depth": 2,
                "dropped_messages": 0,
                "skipped_files": 1,
                "total_files_known": True,
                "total_files_estimated": 3,
                "completed_at": "2025-01-01T00:00:00",
                "large_file_warnings": 0,
                "max_file_size_bytes": 0,
            }

    service = ExtractorService(
        output_queue=output_queue,
        file_processor_factory=MetricsProcessor,
    )

    request = ExtractionRequest(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(".txt",),
        exclude_files=(),
        exclude_folders=(),
        output_file_name=str(tmp_path / "out.txt"),
    )

    def noop_progress(*_args: object) -> None:
        return None

    thread = service.start_extraction(
        request=request,
        progress_callback=noop_progress,
    )
    thread.join(timeout=1)

    metrics_payload = None
    while not output_queue.empty():
        kind, payload = output_queue.get_nowait()
        if kind == "state" and isinstance(payload, dict):
            metrics_payload = payload.get("metrics")

    assert metrics_payload is not None
    assert metrics_payload["processed_files"] == 3
    assert metrics_payload["skipped_files"] == 1
    assert "total_files_known" in metrics_payload
    assert "completed_at" in metrics_payload
    assert "service_dropped_messages" in metrics_payload
    assert "service_dropped_state_messages" in metrics_payload


# Fix: Q-106
def test_cancel_drops_oldest_message_when_queue_full() -> None:
    queue: Queue[tuple[str, object]] = Queue(maxsize=1)
    queue.put(("info", "existing"))
    service = ExtractorService(output_queue=queue)
    service._thread = type("AliveThread", (), {"is_alive": lambda self: True})()

    service.cancel()

    assert service._cancel_event.is_set()
    remaining = queue.get_nowait()
    assert remaining == ("info", "Extraction cancellation requested")


# Fix: Q-106
def test_enqueue_control_message_preserves_state_only_queue() -> None:
    queue: Queue[tuple[str, object]] = Queue(maxsize=2)
    service = ExtractorService(output_queue=queue)

    queue.put(("state", {"result": "pending"}))
    queue.put(("state", {"result": "running"}))

    service._enqueue_control_message("info", "update")

    drained = list(queue.queue)
    assert all(level == "state" for level, _ in drained)
    assert all(payload != "update" for _, payload in drained)
    assert getattr(service, "_dropped_control_messages") >= 1


# Fix: Q-106
def test_error_path_enqueues_message_when_queue_full(tmp_path: Path) -> None:
    queue: Queue[tuple[str, object]] = Queue(maxsize=1)
    queue.put(("info", "existing"))

    class ExplodingProcessor(DummyFileProcessor):
        def extract_files(self, *args, **kwargs):  # type: ignore[override]
            raise RuntimeError("boom")

    service = ExtractorService(
        output_queue=queue,
        file_processor_factory=ExplodingProcessor,
    )

    request = ExtractionRequest(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(".txt",),
        exclude_files=(),
        exclude_folders=(),
        output_file_name=str(tmp_path / "out.txt"),
    )

    def noop_progress(*_args: object) -> None:
        return None

    thread = service.start_extraction(request=request, progress_callback=noop_progress)
    thread.join(timeout=1)

    messages: list[tuple[str, object]] = []
    while not queue.empty():
        messages.append(queue.get_nowait())

    assert all(message != ("info", "existing") for message in messages)
    assert any(
        level == "state" and isinstance(payload, dict) and payload.get("result") == "error"
        for level, payload in messages
    )
    last_state = service.get_last_state_payload()
    assert last_state and last_state.get("message")
