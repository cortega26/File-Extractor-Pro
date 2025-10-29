"""Tests for the file extraction workflow."""

from __future__ import annotations

import hashlib
import os
import queue
from pathlib import Path
from typing import Any, List, Tuple

import processor
from constants import CHUNK_SIZE
from file_extractor import DEFAULT_EXCLUDE, FileProcessor


def test_extract_files_writes_expected_output_and_queue_messages(
    tmp_path: Path,
) -> None:
    """Ensure end-to-end extraction writes output and reports via the queue."""

    spec_file = tmp_path / "README.md"
    spec_file.write_text("specification", encoding="utf-8")

    data_file = tmp_path / "notes.txt"
    data_file.write_text("hello world", encoding="utf-8")

    output_path = tmp_path / "extraction.txt"

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    progress_updates: List[Tuple[int, int]] = []

    def progress_callback(processed: int, total: int) -> None:
        progress_updates.append((processed, total))

    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[".txt", ".md"],
        exclude_files=list(DEFAULT_EXCLUDE),
        exclude_folders=list(DEFAULT_EXCLUDE),
        output_file_name=str(output_path),
        progress_callback=progress_callback,
    )

    assert output_path.exists(), "Extraction should create the output file"

    output_text = output_path.read_text(encoding="utf-8")
    readme_index = output_text.index("README.md")
    notes_index = output_text.index("notes.txt")
    assert readme_index < notes_index, "Specification files should be processed first"

    assert progress_updates, "Progress callback should be invoked"
    first_processed, first_total = progress_updates[0]
    final_processed, final_total = progress_updates[-1]
    assert first_processed == 0
    assert first_total == final_total
    assert final_processed == final_total >= 1

    messages = []
    while not message_queue.empty():
        messages.append(message_queue.get_nowait())

    assert any(
        level == "info" and "Extraction complete" in message
        for level, message in messages
    ), "Final queue message should summarise the run"
    assert any(
        level == "info" and "Extraction metrics" in message
        for level, message in messages
    ), "Metrics summary should be enqueued for observability"

    # Extraction summary tracks extensions and individual files.
    summary = processor.extraction_summary
    assert summary[".txt"]["count"] >= 1
    assert summary[str(data_file)]["hash"], "File hash should be recorded"


# Fix: Q-102
def test_extract_files_progress_denominator_remains_stable(tmp_path: Path) -> None:
    """Progress updates should use a stable denominator across directories."""

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()

    (first_dir / "a.txt").write_text("alpha", encoding="utf-8")
    (second_dir / "b.txt").write_text("bravo", encoding="utf-8")

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    progress_updates: List[Tuple[int, int]] = []

    def progress_callback(processed: int, total: int) -> None:
        progress_updates.append((processed, total))

    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[".txt"],
        exclude_files=list(DEFAULT_EXCLUDE),
        exclude_folders=list(DEFAULT_EXCLUDE),
        output_file_name=str(tmp_path / "out.txt"),
        progress_callback=progress_callback,
    )

    assert progress_updates, "Progress callback should have been invoked"
    first_processed, first_total = progress_updates[0]
    final_processed, final_total = progress_updates[-1]
    assert first_total == final_total == 2
    assert first_processed == 0
    assert first_processed <= first_total
    assert final_processed == final_total == 2


def test_process_file_missing_emits_queue_error(tmp_path: Path) -> None:
    """Processing a missing file should push an error message onto the queue."""

    output_path = tmp_path / "output.txt"
    missing_file = tmp_path / "absent.txt"

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    with open(output_path, "w", encoding="utf-8") as output:
        processor.process_file(str(missing_file), output)

    assert not processor.processed_files, "No files should be marked as processed"

    messages = []
    while not message_queue.empty():
        messages.append(message_queue.get_nowait())

    assert any(level == "error" for level, _ in messages), "Queue must record the error"
    assert output_path.read_text(encoding="utf-8") == ""


def test_process_file_unicode_decode_error_reported(tmp_path: Path) -> None:
    """Binary files that fail to decode should emit an error without crashing."""

    binary_file = tmp_path / "binary.bin"
    binary_file.write_bytes(b"\xff\xfe\x00\x00")
    output_path = tmp_path / "output.txt"

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    with open(output_path, "w", encoding="utf-8") as output:
        processor.process_file(str(binary_file), output)

    messages = []
    while not message_queue.empty():
        messages.append(message_queue.get_nowait())

    assert any(
        level == "error" and "Cannot decode" in message for level, message in messages
    )
    assert output_path.read_text(encoding="utf-8") == ""


def test_process_file_streams_content_without_buffering(tmp_path: Path) -> None:
    """Large files should be streamed to the output file without buffering fully."""

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    large_file = tmp_path / "large.txt"
    repeated_block = "abcdefghij" * (CHUNK_SIZE // 10 + 5)
    large_file.write_text(repeated_block, encoding="utf-8")

    output_path = tmp_path / "output.txt"

    with open(output_path, "w", encoding="utf-8") as output:
        processor.process_file(str(large_file), output)

    output_text = output_path.read_text(encoding="utf-8")
    normalized_path = str(large_file.resolve()).replace(os.path.sep, "/")
    assert output_text.startswith(f"{normalized_path}:\n")
    assert output_text.endswith("\n\n\n"), "Output should include trailing separators"
    assert repeated_block in output_text, "File content should be present in the output"

    expected_hash = hashlib.sha256(repeated_block.encode("utf-8")).hexdigest()
    summary_entry = processor.extraction_summary[str(large_file)]
    assert summary_entry["hash"] == expected_hash
    assert summary_entry["size"] == len(repeated_block)


def test_process_file_allows_large_files_beyond_soft_cap(
    monkeypatch, tmp_path: Path
) -> None:
    """Large files exceeding the configured cap should still be processed."""

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue(maxsize=4)
    processor = FileProcessor(message_queue, max_file_size_mb=50)

    large_file = tmp_path / "oversized.txt"
    large_file.write_text("content", encoding="utf-8")
    output_path = tmp_path / "output.txt"

    real_getsize = os.path.getsize

    def fake_getsize(path: str) -> int:
        if Path(path) == large_file:
            return 200 * 1024 * 1024
        return real_getsize(path)

    monkeypatch.setattr(os.path, "getsize", fake_getsize)

    with open(output_path, "w", encoding="utf-8") as output:
        processor.process_file(str(large_file), output)

    output_text = output_path.read_text(encoding="utf-8")
    assert "oversized.txt" in output_text

    warnings = []
    while not message_queue.empty():
        warnings.append(message_queue.get_nowait())

    assert any(level == "warning" for level, _ in warnings)


# Fix: Q-105
def test_file_processor_estimates_available_memory(monkeypatch) -> None:
    """The processor should derive a soft cap from available memory when unset."""

    estimated_bytes = 32 * 1024 * 1024
    monkeypatch.setattr(
        processor, "_estimate_available_memory_bytes", lambda: estimated_bytes
    )

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    instance = FileProcessor(message_queue)

    assert getattr(instance, "_max_file_size_bytes", None) == estimated_bytes


# Fix: Q-105
def test_process_file_retries_with_smaller_chunks_on_memory_error(
    tmp_path: Path,
) -> None:
    """Memory pressure during streaming should trigger a retry with smaller chunks."""

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()

    class MemoryPressureProcessor(FileProcessor):
        def __init__(self, output_queue: queue.Queue[Tuple[str, str]]) -> None:
            super().__init__(output_queue)
            self.attempts = 0

        def _stream_file_contents(self, **kwargs: Any) -> str:  # type: ignore[override]
            self.attempts += 1
            if self.attempts == 1:
                raise MemoryError("simulated pressure")
            return super()._stream_file_contents(**kwargs)

    processor = MemoryPressureProcessor(message_queue)

    sample_file = tmp_path / "retry.txt"
    sample_file.write_text("retry payload", encoding="utf-8")

    output_path = tmp_path / "output.txt"
    with open(output_path, "w", encoding="utf-8") as output:
        processor.process_file(str(sample_file), output)

    assert processor.attempts == 2
    warnings = list(message_queue.queue)
    assert any("Memory pressure detected" in payload for _, payload in warnings)


# Fix: Q-101
def test_iter_eligible_file_paths_honours_wildcard(tmp_path: Path) -> None:
    """Wildcard extension tokens should include all files in inclusion mode."""

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    include_dir = tmp_path / "nested"
    include_dir.mkdir()
    kept_file = include_dir / "document.xyz"
    kept_file.write_text("payload", encoding="utf-8")

    output_path = tmp_path / "out.txt"
    eligible = list(
        processor._iter_eligible_file_paths(
            folder_path=str(tmp_path),
            mode="inclusion",
            include_hidden=False,
            extensions=("*",),
            exclude_files=(),
            exclude_folders=(),
            output_file_abs=str(output_path),
        )
    )

    assert str(kept_file) in eligible


def test_extract_files_records_metrics(tmp_path: Path) -> None:
    """Extraction runs should expose elapsed time and throughput metrics."""

    (tmp_path / "data.txt").write_text("payload", encoding="utf-8")

    message_queue: queue.Queue[Tuple[str, object]] = queue.Queue()
    processor = FileProcessor(message_queue)

    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[".txt"],
        exclude_files=list(DEFAULT_EXCLUDE),
        exclude_folders=list(DEFAULT_EXCLUDE),
        output_file_name=str(tmp_path / "out.txt"),
    )

    metrics = processor.last_run_metrics
    assert metrics["processed_files"] == metrics["total_files"] == 1
    assert metrics["elapsed_seconds"] >= 0.0
    assert metrics["files_per_second"] >= 0.0
    assert metrics["max_queue_depth"] >= 0
    assert metrics["dropped_messages"] == 0
    assert metrics["skipped_files"] == 0


def test_extract_files_runs_single_directory_walk(monkeypatch, tmp_path: Path) -> None:
    """The extraction should traverse the filesystem only once for performance."""

    (tmp_path / "keep.txt").write_text("data", encoding="utf-8")
    (tmp_path / "skip.bin").write_text("binary", encoding="utf-8")

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    progress_updates: List[Tuple[int, int]] = []

    def progress_callback(processed: int, total: int) -> None:
        progress_updates.append((processed, total))

    walk_calls = 0
    real_walk = os.walk

    def counting_walk(*args: Any, **kwargs: Any):
        nonlocal walk_calls
        walk_calls += 1
        yield from real_walk(*args, **kwargs)

    monkeypatch.setattr(os, "walk", counting_walk)

    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[".txt"],
        exclude_files=list(DEFAULT_EXCLUDE),
        exclude_folders=list(DEFAULT_EXCLUDE),
        output_file_name=str(tmp_path / "out.txt"),
        progress_callback=progress_callback,
    )

    assert walk_calls == 1, "os.walk should only be invoked once per extraction"

    assert progress_updates, "Progress callback should report at least one update"
    first_processed, first_total = progress_updates[0]
    final_processed, final_total = progress_updates[-1]
    assert first_processed == 0
    assert first_total == final_total == 1
    assert final_processed == final_total


# Fix: Q-102
def test_extract_files_falls_back_to_indeterminate_progress_on_memory_error(
    tmp_path: Path,
) -> None:
    """Enumerating files should fall back gracefully when memory is exhausted."""

    class HungryProcessor(FileProcessor):
        def __init__(self, queue_obj: queue.Queue[Tuple[str, object]]) -> None:
            super().__init__(queue_obj)
            self.calls = 0

        def _iter_eligible_file_paths(self, *args: Any, **kwargs: Any):  # type: ignore[override]
            self.calls += 1
            if self.calls == 1:
                raise MemoryError("simulated enumeration failure")
            yield from super()._iter_eligible_file_paths(*args, **kwargs)

    (tmp_path / "data.txt").write_text("payload", encoding="utf-8")

    message_queue: queue.Queue[Tuple[str, object]] = queue.Queue()
    processor = HungryProcessor(message_queue)

    progress_updates: List[Tuple[int, int]] = []

    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[".txt"],
        exclude_files=list(DEFAULT_EXCLUDE),
        exclude_folders=list(DEFAULT_EXCLUDE),
        output_file_name=str(tmp_path / "out.txt"),
        progress_callback=lambda processed, total: progress_updates.append((processed, total)),
    )

    assert processor.calls == 2
    assert progress_updates[0][1] == -1
    assert progress_updates[-1][1] == -1
    warnings = [payload for level, payload in message_queue.queue if level == "warning"]
    assert any("indeterminate" in str(message).lower() for message in warnings)
    metrics = processor.last_run_metrics
    assert metrics["total_files"] == -1


# Fix: Q-105
def test_extract_files_skips_files_after_persistent_memory_errors(tmp_path: Path) -> None:
    """Repeated memory pressure should skip the file without aborting the run."""

    class PersistentProcessor(FileProcessor):
        def _stream_file_contents(self, **_: Any) -> str:  # type: ignore[override]
            raise MemoryError("persistent failure")

    sample = tmp_path / "huge.txt"
    sample.write_text("payload", encoding="utf-8")

    message_queue: queue.Queue[Tuple[str, object]] = queue.Queue()
    processor = PersistentProcessor(message_queue)

    progress_updates: List[Tuple[int, int]] = []

    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=[".txt"],
        exclude_files=list(DEFAULT_EXCLUDE),
        exclude_folders=list(DEFAULT_EXCLUDE),
        output_file_name=str(tmp_path / "out.txt"),
        progress_callback=lambda processed, total: progress_updates.append((processed, total)),
    )

    metrics = processor.last_run_metrics
    assert metrics["processed_files"] == 0
    assert metrics["skipped_files"] == 1
    assert progress_updates[0] == (0, 1)
    messages = list(message_queue.queue)
    assert any("skipped file" in str(payload).lower() for _, payload in messages)


def test_enqueue_message_applies_backpressure_when_queue_full() -> None:
    """Processor should drop the oldest message when the status queue is full."""

    message_queue: queue.Queue[Tuple[str, object]] = queue.Queue(maxsize=2)
    processor = FileProcessor(message_queue)

    message_queue.put(("info", "oldest"))
    message_queue.put(("info", "older"))

    processor._enqueue_message("info", "new message")

    assert message_queue.qsize() == 2
    first, second = message_queue.get_nowait(), message_queue.get_nowait()
    assert first == ("info", "new message")
    assert second == ("info", "older")
    assert processor._dropped_messages >= 1


def test_enqueue_message_preserves_state_when_queue_full() -> None:
    """State messages should survive backpressure attempts."""

    message_queue: queue.Queue[Tuple[str, object]] = queue.Queue(maxsize=2)
    processor = FileProcessor(message_queue)

    message_queue.put(("state", {"result": "pending"}))
    message_queue.put(("info", "existing"))

    processor._enqueue_message("info", "new message")

    drained: List[Tuple[str, object]] = []
    while not message_queue.empty():
        drained.append(message_queue.get_nowait())

    assert drained[0] == ("info", "new message")
    assert drained[1][0] == "state"
    assert any(payload == "new message" for _, payload in drained)
    assert processor._dropped_messages >= 1


def test_enqueue_message_replaces_oldest_state_when_only_states_present() -> None:
    """New state updates should displace the oldest state entry when necessary."""

    message_queue: queue.Queue[Tuple[str, object]] = queue.Queue(maxsize=2)
    processor = FileProcessor(message_queue)

    first_state = ("state", {"result": "pending"})
    second_state = ("state", {"result": "running"})
    message_queue.put(first_state)
    message_queue.put(second_state)

    processor._enqueue_message("state", {"result": "success"})

    drained: list[Tuple[str, object]] = []
    while not message_queue.empty():
        drained.append(message_queue.get_nowait())

    assert len(drained) == 2
    assert first_state not in drained
    assert any(
        isinstance(payload, dict) and payload.get("result") == "success"
        for _, payload in drained
    )


# Fix: Q-106
def test_enqueue_message_survives_concurrent_refill() -> None:
    """Concurrent producers should not prevent the new payload from being enqueued."""

    class RacingQueue(queue.Queue[Tuple[str, object]]):
        def __init__(self) -> None:
            super().__init__(maxsize=2)
            self.failures = 0

        def put_nowait(self, item: Tuple[str, object]) -> None:  # type: ignore[override]
            if self.failures < 1 and item[1] == "new message":
                self.failures += 1
                raise queue.Full
            return super().put_nowait(item)

    racing_queue: RacingQueue = RacingQueue()
    racing_queue.put(("info", "existing-1"))
    racing_queue.put(("info", "existing-2"))

    processor = FileProcessor(racing_queue)
    processor._enqueue_message("info", "new message")

    drained: list[Tuple[str, object]] = []
    while not racing_queue.empty():
        drained.append(racing_queue.get_nowait())

    assert any(payload == "new message" for _, payload in drained)
    assert len(drained) == 2


def test_build_summary_and_reset_state(tmp_path: Path) -> None:
    """The processor should expose a structured summary snapshot and reset cleanly."""

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    sample_file = tmp_path / "example.txt"
    sample_content = "sample payload"
    sample_file.write_text(sample_content, encoding="utf-8")

    with open(tmp_path / "out.txt", "w", encoding="utf-8") as output:
        processor.process_file(str(sample_file), output)

    summary = processor.build_summary()
    assert summary["total_files"] == 1
    assert summary["total_size"] == len(sample_content)
    assert summary["extension_summary"][".txt"]["count"] == 1
    assert str(sample_file) in summary["file_details"]

    processor.reset_state()
    assert not processor.processed_files
    cleared_summary = processor.build_summary()
    assert cleared_summary["total_files"] == 0
    assert not cleared_summary["file_details"]
