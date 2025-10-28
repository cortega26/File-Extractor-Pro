"""Tests for the file extraction workflow."""

from __future__ import annotations

import hashlib
import os
import queue
from pathlib import Path
from typing import Any, List, Tuple

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
    assert first_processed == 1
    assert final_processed == final_total >= 1

    messages = []
    while not message_queue.empty():
        messages.append(message_queue.get_nowait())

    assert any(
        level == "info" and "Extraction complete" in message
        for level, message in messages
    ), "Final queue message should summarise the run"

    # Extraction summary tracks extensions and individual files.
    summary = processor.extraction_summary
    assert summary[".txt"]["count"] >= 1
    assert summary[str(data_file)]["hash"], "File hash should be recorded"


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
    final_processed, final_total = progress_updates[-1]
    assert final_total == 1
    assert final_processed == final_total


def test_enqueue_message_applies_backpressure_when_queue_full() -> None:
    """Processor should drop the oldest message when the status queue is full."""

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue(maxsize=2)
    processor = FileProcessor(message_queue)

    message_queue.put(("info", "oldest"))
    message_queue.put(("info", "older"))

    processor._enqueue_message("info", "new message")

    contents = [message_queue.get_nowait(), message_queue.get_nowait()]

    assert ("info", "new message") in contents
    assert all(message != ("info", "oldest") for message in contents)
