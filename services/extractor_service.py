"""Extraction service coordinating worker lifecycle and messaging."""

from __future__ import annotations

import asyncio
import threading
from queue import Queue
from typing import Awaitable, Callable, Sequence

from logging_utils import logger
from processor import FileProcessor

ProgressCallback = Callable[[int, int], Awaitable[None]]


class ExtractorService:
    """Manage background extraction execution and status dispatching."""

    def __init__(
        self,
        *,
        queue_max_size: int = 256,
        file_processor_factory: Callable[[Queue], FileProcessor] = FileProcessor,
        output_queue: Queue | None = None,
    ) -> None:
        self.output_queue = output_queue or Queue(maxsize=queue_max_size)
        self._file_processor = file_processor_factory(self.output_queue)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def file_processor(self) -> FileProcessor:
        """Expose the underlying file processor for reporting access."""

        return self._file_processor

    def start_extraction(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: Sequence[str],
        exclude_files: Sequence[str],
        exclude_folders: Sequence[str],
        output_file_name: str,
        progress_callback: ProgressCallback,
    ) -> threading.Thread:
        """Start a managed background extraction worker."""

        with self._lock:
            if self.is_running():
                raise RuntimeError("Extraction already in progress")

            self._thread = threading.Thread(
                target=self._run_extraction,
                args=(
                    folder_path,
                    mode,
                    include_hidden,
                    extensions,
                    exclude_files,
                    exclude_folders,
                    output_file_name,
                    progress_callback,
                ),
                daemon=True,
            )
            self._thread.start()
            return self._thread

    def is_running(self) -> bool:
        """Return whether the extraction worker is active."""

        return self._thread is not None and self._thread.is_alive()

    def cancel(self) -> None:
        """Signal cancellation to UI consumers via status queue."""

        if not self.is_running():
            return

        self.output_queue.put(("info", "Extraction cancellation requested"))
        logger.info("Extraction cancellation requested by user")

    def _run_extraction(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: Sequence[str],
        exclude_files: Sequence[str],
        exclude_folders: Sequence[str],
        output_file_name: str,
        progress_callback: ProgressCallback,
    ) -> None:
        """Execute extraction inside a dedicated event loop."""

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        try:
            loop.run_until_complete(
                self._file_processor.extract_files(
                    folder_path,
                    mode,
                    include_hidden,
                    extensions,
                    exclude_files,
                    exclude_folders,
                    output_file_name,
                    progress_callback=progress_callback,
                )
            )
        except Exception as exc:  # pragma: no cover - logged and surfaced to UI
            logger.error("Error in extraction worker: %s", exc)
            self.output_queue.put(("error", f"Extraction error: {exc}"))
        finally:
            loop.close()
            with self._lock:
                self._loop = None
                self._thread = None


__all__ = ["ExtractorService", "ProgressCallback"]
