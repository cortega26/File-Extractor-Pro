"""Extraction service coordinating worker lifecycle and messaging."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from queue import Empty, Full, Queue
from typing import Any, Callable, Dict, Sequence

from logging_utils import logger
from processor import ExtractionCancelled, FileProcessor

ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True)
class ExtractionRequest:
    """Immutable representation of extraction parameters."""

    folder_path: str
    mode: str
    include_hidden: bool
    extensions: tuple[str, ...]
    exclude_files: tuple[str, ...]
    exclude_folders: tuple[str, ...]
    output_file_name: str

    def as_kwargs(self) -> Dict[str, Any]:
        """Convert the request into keyword arguments for execution."""

        return {
            "folder_path": self.folder_path,
            "mode": self.mode,
            "include_hidden": self.include_hidden,
            "extensions": self.extensions,
            "exclude_files": self.exclude_files,
            "exclude_folders": self.exclude_folders,
            "output_file_name": self.output_file_name,
        }


@dataclass(frozen=True)
class ExtractionSummary:
    """Typed representation of a completed extraction summary."""

    total_files: int
    total_size: int
    extension_summary: Dict[str, Dict[str, int]]
    file_details: Dict[str, Dict[str, Any]]

    def as_payload(self) -> Dict[str, Any]:
        """Return a serialisable payload for reporting."""

        return {
            "timestamp": datetime.now().isoformat(),
            "total_files": self.total_files,
            "total_size": self.total_size,
            "extension_summary": self.extension_summary,
            "file_details": self.file_details,
        }


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
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()

    @property
    def file_processor(self) -> FileProcessor:
        """Expose the underlying file processor for reporting access."""

        return self._file_processor

    def reset_state(self) -> None:
        """Clear processor state prior to a new extraction run."""

        self._file_processor.reset_state()

    def get_summary(self) -> ExtractionSummary:
        """Return a structured snapshot of the latest extraction results."""

        snapshot = self._file_processor.build_summary()
        return ExtractionSummary(
            total_files=int(snapshot["total_files"]),
            total_size=int(snapshot["total_size"]),
            extension_summary=snapshot["extension_summary"],
            file_details=snapshot["file_details"],
        )

    def generate_report(self, *, output_path: str = "extraction_report.json") -> str:
        """Serialise the latest extraction summary to disk."""

        summary = self.get_summary()
        if summary.total_files == 0 and not summary.file_details:
            raise ValueError("No extraction data available to report")

        payload = summary.as_payload()
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

        logger.info("Extraction report written to %s", output_path)
        return output_path

    def start_extraction(
        self,
        *,
        request: ExtractionRequest | None = None,
        folder_path: str | None = None,
        mode: str | None = None,
        include_hidden: bool | None = None,
        extensions: Sequence[str] | None = None,
        exclude_files: Sequence[str] | None = None,
        exclude_folders: Sequence[str] | None = None,
        output_file_name: str | None = None,
        progress_callback: ProgressCallback,
    ) -> threading.Thread:
        """Start a managed background extraction worker."""

        if request is not None:
            request_kwargs = request.as_kwargs()
            folder_path = request_kwargs["folder_path"]
            mode = request_kwargs["mode"]
            include_hidden = request_kwargs["include_hidden"]
            extensions = request_kwargs["extensions"]
            exclude_files = request_kwargs["exclude_files"]
            exclude_folders = request_kwargs["exclude_folders"]
            output_file_name = request_kwargs["output_file_name"]

        if progress_callback is None:
            raise ValueError("progress_callback must be provided")

        required_params = {
            "folder_path": folder_path,
            "mode": mode,
            "include_hidden": include_hidden,
            "extensions": extensions,
            "exclude_files": exclude_files,
            "exclude_folders": exclude_folders,
            "output_file_name": output_file_name,
        }
        missing = [name for name, value in required_params.items() if value is None]
        if missing:
            raise ValueError(
                "Missing extraction parameters: " + ", ".join(sorted(missing))
            )

        resolved_extensions = tuple(extensions or ())
        resolved_exclude_files = tuple(exclude_files or ())
        resolved_exclude_folders = tuple(exclude_folders or ())

        with self._lock:
            if self.is_running():
                raise RuntimeError("Extraction already in progress")

            self._cancel_event.clear()
            self._thread = threading.Thread(
                target=self._run_extraction,
                args=(
                    str(folder_path),
                    str(mode),
                    bool(include_hidden),
                    resolved_extensions,
                    resolved_exclude_files,
                    resolved_exclude_folders,
                    str(output_file_name),
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

        if not self._cancel_event.is_set():
            self.output_queue.put(("info", "Extraction cancellation requested"))
            logger.info("Extraction cancellation requested by user")

        self._cancel_event.set()

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
        """Execute extraction inside a dedicated worker thread."""

        state_payload: dict[str, str] = {"status": "finished", "result": "success"}
        try:
            self._file_processor.extract_files(
                folder_path,
                mode,
                include_hidden,
                extensions,
                exclude_files,
                exclude_folders,
                output_file_name,
                progress_callback=progress_callback,
                is_cancelled=self._cancel_event.is_set,
            )
        except ExtractionCancelled:
            logger.info("Extraction cancelled before completion")
            state_payload["result"] = "cancelled"
            self.output_queue.put(("info", "Extraction cancelled"))
        except Exception as exc:  # pragma: no cover - logged and surfaced to UI
            logger.error("Error in extraction worker: %s", exc)
            self.output_queue.put(("error", f"Extraction error: {exc}"))
            state_payload["result"] = "error"
            state_payload["message"] = str(exc)
        finally:
            self._publish_state_update(state_payload)
            with self._lock:
                self._thread = None

    def _publish_state_update(self, payload: dict[str, str]) -> None:
        """Publish a non-blocking service state update message."""

        message = ("state", payload)
        try:
            self.output_queue.put_nowait(message)
            return
        except Full:
            pass

        # Fix: audit/backlog/Q-106 - ensure terminal state messages are retained.
        preserved_states: list[tuple[str, object]] = []
        evicted: tuple[str, object] | None = None
        while evicted is None:
            try:
                candidate = self.output_queue.get_nowait()
            except Empty:
                break
            if candidate[0] == "state":
                preserved_states.append(candidate)
                continue
            evicted = candidate
        if evicted is None and preserved_states:
            evicted = preserved_states.pop(0)
            logger.warning(
                "Output queue saturated with state updates; dropping oldest state"
            )
        for state_message in preserved_states:
            try:
                self.output_queue.put_nowait(state_message)
            except Full:
                logger.warning(
                    "Failed to restore preserved state message after saturation"
                )
        if evicted is None:
            logger.warning(
                "Unable to evict message despite saturation; dropping state update"
            )
            return
        try:
            self.output_queue.put_nowait(message)
        except Full:
            logger.warning("Dropping state update due to repeated saturation")


__all__ = [
    "ExtractionRequest",
    "ExtractorService",
    "ExtractionSummary",
    "ProgressCallback",
]
