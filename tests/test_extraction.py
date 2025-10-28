"""Tests for the asynchronous file extraction workflow."""

from __future__ import annotations

import asyncio
import queue
from pathlib import Path
from typing import List, Tuple

import pytest

from file_extractor import DEFAULT_EXCLUDE, FileProcessor


def test_extract_files_writes_expected_output_and_queue_messages(tmp_path: Path) -> None:
    """Ensure end-to-end extraction writes output and reports via the queue."""

    spec_file = tmp_path / "README.md"
    spec_file.write_text("specification", encoding="utf-8")

    data_file = tmp_path / "notes.txt"
    data_file.write_text("hello world", encoding="utf-8")

    output_path = tmp_path / "extraction.txt"

    message_queue: queue.Queue[Tuple[str, str]] = queue.Queue()
    processor = FileProcessor(message_queue)

    progress_updates: List[Tuple[int, int]] = []

    async def progress_callback(processed: int, total: int) -> None:
        progress_updates.append((processed, total))

    async def run_extraction() -> None:
        await processor.extract_files(
            folder_path=str(tmp_path),
            mode="inclusion",
            include_hidden=False,
            extensions=[".txt", ".md"],
            exclude_files=list(DEFAULT_EXCLUDE),
            exclude_folders=list(DEFAULT_EXCLUDE),
            output_file_name=str(output_path),
            progress_callback=progress_callback,
        )

    asyncio.run(run_extraction())

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
