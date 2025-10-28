"""Unit tests for the extractor service layer."""

from __future__ import annotations

import threading
from queue import Queue

import pytest

from services.extractor_service import ExtractorService


class DummyFileProcessor:
    """Test double that records whether extraction was invoked."""

    def __init__(self, output_queue: Queue) -> None:
        self.output_queue = output_queue
        self.called = threading.Event()

    async def extract_files(self, *args, progress_callback):  # type: ignore[override]
        await progress_callback(1, 1)
        self.called.set()


def test_start_extraction_runs_worker(tmp_path):
    progress_called = threading.Event()

    async def progress_callback(processed: int, total: int) -> None:
        progress_called.set()

    service = ExtractorService(
        file_processor_factory=DummyFileProcessor,
        output_queue=Queue(maxsize=4),
    )

    thread = service.start_extraction(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[],
        exclude_files=[],
        exclude_folders=[],
        output_file_name=str(tmp_path / "out.txt"),
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
        async def extract_files(self, *args, progress_callback):  # type: ignore[override]
            await progress_callback(0, 0)
            barrier.wait()

    async def noop_progress(*_args):
        return None

    service = ExtractorService(file_processor_factory=BlockingFileProcessor)
    service.start_extraction(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[],
        exclude_files=[],
        exclude_folders=[],
        output_file_name=str(tmp_path / "out.txt"),
        progress_callback=noop_progress,
    )

    with pytest.raises(RuntimeError):
        service.start_extraction(
            folder_path=str(tmp_path),
            mode="inclusion",
            include_hidden=False,
            extensions=[],
            exclude_files=[],
            exclude_folders=[],
            output_file_name=str(tmp_path / "out.txt"),
            progress_callback=noop_progress,
        )

    barrier.set()
