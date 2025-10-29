"""File processing logic for File Extractor Pro."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from copy import deepcopy
from datetime import datetime
from queue import Empty, Full, Queue
from time import perf_counter
from typing import IO, Any, Callable, Dict, Iterable, MutableMapping, Sequence, Set

from constants import CHUNK_SIZE, SPECIFICATION_FILES
from logging_utils import logger


class ExtractionCancelled(RuntimeError):
    """Raised when an extraction run is cancelled mid-flight."""


class FileProcessor:
    """Enhanced file processor with improved error handling and performance."""

    def __init__(
        self,
        output_queue: Queue,
        *,
        max_file_size_mb: int | None = None,
    ) -> None:
        """Initialise the processor with optional safeguards.

        Args:
            output_queue: Queue used to communicate status updates.
            max_file_size_mb: Optional soft cap for file sizes. ``None``
                disables the cap and relies on streaming reads.
        """

        self.output_queue = output_queue
        self.extraction_summary: Dict[str, Any] = {}
        self.processed_files: Set[str] = set()
        self._cache: Dict[str, Any] = {}
        self._max_file_size_bytes: int | None = None
        self.configure_max_file_size(max_file_size_mb)
        self._max_queue_depth: int = 0
        self._last_run_metrics: Dict[str, float | int] = {}

    # Fix: Q-105
    def configure_max_file_size(self, max_file_size_mb: int | None) -> None:
        """Adjust the soft file size cap used for warning emissions."""

        if max_file_size_mb is None:
            self._max_file_size_bytes = None
            return
        if max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive when provided")
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _record_queue_depth(self) -> None:
        """Track the maximum observed queue depth for instrumentation."""

        try:
            current_depth = self.output_queue.qsize()
        except NotImplementedError:
            return
        if current_depth > self._max_queue_depth:
            self._max_queue_depth = current_depth

    # Fix: Q-106
    def _enqueue_message(self, level: str, message: str) -> None:
        """Safely enqueue status messages without blocking the worker thread."""

        drained: list[tuple[str, object]] = []
        try:
            self.output_queue.put_nowait((level, message))
            self._record_queue_depth()
            return
        except Full:
            while True:
                try:
                    drained.append(self.output_queue.get_nowait())
                except Empty:
                    break

        drop_index: int | None = None
        for index, candidate in enumerate(drained):
            if candidate[0] != "state":
                drop_index = index
                break

        if drop_index is None and drained:
            drop_index = 0
            logger.warning(
                "Status queue saturated with state updates only; discarding oldest state"
            )

        if drop_index is not None:
            drained.pop(drop_index)

        for payload in drained:
            try:
                self.output_queue.put_nowait(payload)
                self._record_queue_depth()
            except Full:
                logger.warning("Queue remained saturated while restoring messages")
                return

        try:
            self.output_queue.put_nowait((level, message))
            self._record_queue_depth()
        except Full:
            logger.warning(
                "Dropping status message after repeated saturation: %s", message
            )

    def process_specifications(
        self,
        directory_path: str,
        output_file: IO[str],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        """Process specification files first with enhanced error handling."""

        for spec_file in SPECIFICATION_FILES:
            if is_cancelled and is_cancelled():
                raise ExtractionCancelled("Extraction cancelled before specs processed")

            try:
                file_path = os.path.join(directory_path, spec_file)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    logger.info("Processing specification file: %s", spec_file)
                    self.process_file(
                        file_path,
                        output_file,
                        is_cancelled=is_cancelled,
                    )
                    self.processed_files.add(file_path)
            except ExtractionCancelled:
                raise
            except Exception as exc:
                logger.error(
                    "Error processing specification file %s: %s", spec_file, exc
                )
                self._enqueue_message("error", f"Error processing {spec_file}: {exc}")

    def process_file(
        self,
        file_path: str,
        output_file: IO[str],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        """Process individual file with improved error handling and memory management."""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"Permission denied: {file_path}")

            file_size = os.path.getsize(file_path)
            if (
                self._max_file_size_bytes is not None
                and file_size > self._max_file_size_bytes
            ):
                logger.warning(
                    "File %s exceeds configured max size (%s MB); continuing via streaming",
                    file_path,
                    int(self._max_file_size_bytes / (1024 * 1024)),
                )
                self._enqueue_message(
                    "warning",
                    (
                        "Processing large file beyond configured threshold: "
                        f"{file_path}"
                    ),
                )
            # Fix: audit/backlog/Q-105 - rely on streaming reads instead of a hard cap.

            normalized_path = os.path.normpath(file_path).replace(os.path.sep, "/")

            file_ext = os.path.splitext(file_path)[1]
            sha256 = hashlib.sha256()

            can_restore_output = all(
                hasattr(output_file, method) for method in ("tell", "seek", "truncate")
            )
            start_position = 0
            if can_restore_output:
                start_position = output_file.tell()

            try:
                header_written = False

                with open(file_path, "r", encoding="utf-8") as source:
                    while True:
                        if is_cancelled and is_cancelled():
                            raise ExtractionCancelled(
                                "Extraction cancelled during file processing"
                            )

                        chunk = source.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        if not header_written:
                            output_file.write(f"{normalized_path}:\n")
                            header_written = True

                        sha256.update(chunk.encode("utf-8"))
                        output_file.write(chunk)

                if not header_written:
                    output_file.write(f"{normalized_path}:\n")

                output_file.write("\n\n\n")

            except ExtractionCancelled:
                if can_restore_output:
                    output_file.seek(start_position)
                    output_file.truncate()
                raise
            except Exception:
                if can_restore_output:
                    output_file.seek(start_position)
                    output_file.truncate()
                raise

            file_hash = sha256.hexdigest()

            self._update_extraction_summary(file_ext, file_path, file_size, file_hash)

            logger.debug("Successfully processed file: %s", file_path)

        except (UnicodeDecodeError, UnicodeError) as exc:
            logger.warning("Unicode decode error for %s: %s", file_path, exc)
            self._enqueue_message("error", f"Cannot decode file {file_path}: {exc}")
        except Exception as exc:
            logger.error("Error processing file %s: %s", file_path, exc)
            self._enqueue_message("error", f"Error processing {file_path}: {exc}")

    @property
    def last_run_metrics(self) -> Dict[str, float | int]:
        """Return instrumentation metrics captured during the last extraction."""

        return dict(self._last_run_metrics)

    def _update_extraction_summary(
        self, file_ext: str, file_path: str, file_size: int, file_hash: str
    ) -> None:
        """Update extraction summary with thread safety."""
        try:
            if file_ext not in self.extraction_summary:
                self.extraction_summary[file_ext] = {"count": 0, "total_size": 0}

            self.extraction_summary[file_ext]["count"] += 1
            self.extraction_summary[file_ext]["total_size"] += file_size

            self.extraction_summary[file_path] = {
                "size": file_size,
                "hash": file_hash,
                "extension": file_ext,
                "processed_time": datetime.now().isoformat(),
            }
        except Exception as exc:
            logger.error("Error updating extraction summary: %s", exc)

    def reset_state(self) -> None:
        """Reset aggregation state between extraction runs."""

        self.extraction_summary.clear()
        self.processed_files.clear()
        self._cache.clear()

    def build_summary(self) -> Dict[str, Any]:
        """Return an immutable snapshot of the latest extraction summary."""

        extension_summary: Dict[str, Dict[str, int]] = {}
        file_details: Dict[str, Dict[str, Any]] = {}
        total_files = 0
        total_size = 0

        for key, value in self.extraction_summary.items():
            if not isinstance(value, MutableMapping):
                continue

            if {"count", "total_size"}.issubset(value.keys()):
                count = int(value.get("count", 0))
                size = int(value.get("total_size", 0))
                extension_summary[key] = {"count": count, "total_size": size}
                total_files += count
                total_size += size
                continue

            if {"size", "hash", "extension"}.issubset(value.keys()):
                file_details[key] = {
                    "size": int(value.get("size", 0)),
                    "hash": str(value.get("hash", "")),
                    "extension": str(value.get("extension", "")),
                    "processed_time": str(value.get("processed_time", "")),
                }

        return {
            "total_files": total_files,
            "total_size": total_size,
            "extension_summary": deepcopy(extension_summary),
            "file_details": deepcopy(file_details),
        }

    # Fix: Q-102
    def _iter_eligible_file_paths(
        self,
        *,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: Sequence[str],
        exclude_files: Sequence[str],
        exclude_folders: Sequence[str],
        output_file_abs: str,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> Iterable[str]:
        """Yield eligible file paths while respecting cancellation hooks."""

        seen_paths: Set[str] = set()
        extensions_set = set(extensions)

        for root, dirs, files in os.walk(folder_path):
            if is_cancelled and is_cancelled():
                raise ExtractionCancelled("Extraction cancelled during traversal")

            mutable_dirs = list(dirs)
            mutable_files = list(files)

            if not include_hidden:
                mutable_dirs = [
                    directory for directory in mutable_dirs if not directory.startswith(".")
                ]
                mutable_files = [
                    file_name for file_name in mutable_files if not file_name.startswith(".")
                ]

            filtered_dirs = [
                directory
                for directory in mutable_dirs
                if not any(fnmatch.fnmatch(directory, pattern) for pattern in exclude_folders)
            ]
            filtered_files = [
                file_name
                for file_name in mutable_files
                if not any(fnmatch.fnmatch(file_name, pattern) for pattern in exclude_files)
            ]

            dirs[:] = filtered_dirs

            for file_name in filtered_files:
                if is_cancelled and is_cancelled():
                    raise ExtractionCancelled("Extraction cancelled while iterating files")

                file_path = os.path.join(root, file_name)
                if os.path.abspath(file_path) == output_file_abs:
                    continue
                if file_path in self.processed_files or file_path in seen_paths:
                    continue

                file_ext = os.path.splitext(file_name)[1]
                should_process = False
                if mode == "inclusion":
                    should_process = file_ext in extensions_set
                elif mode == "exclusion":
                    should_process = file_ext not in extensions_set

                if not should_process:
                    continue

                seen_paths.add(file_path)
                yield file_path

    def extract_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: Sequence[str],
        exclude_files: Sequence[str],
        exclude_folders: Sequence[str],
        output_file_name: str,
        *,
        progress_callback: Callable[[int, int], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> None:
        """Extract files with improved error handling and progress reporting."""

        # Fix: Q-108 - initialise instrumentation for this run.
        self._max_queue_depth = self.output_queue.qsize()
        self._last_run_metrics = {}
        start_time = perf_counter()

        processed_count = 0

        try:
            output_file_abs = os.path.abspath(output_file_name)

            with open(output_file_name, "w", encoding="utf-8") as output:
                self.process_specifications(
                    folder_path,
                    output,
                    is_cancelled=is_cancelled,
                )

                eligible_paths = list(
                    self._iter_eligible_file_paths(
                        folder_path=folder_path,
                        mode=mode,
                        include_hidden=include_hidden,
                        extensions=extensions,
                        exclude_files=exclude_files,
                        exclude_folders=exclude_folders,
                        output_file_abs=output_file_abs,
                        is_cancelled=is_cancelled,
                    )
                )

                total_files = len(eligible_paths)

                for file_path in eligible_paths:
                    self.process_file(
                        file_path,
                        output,
                        is_cancelled=is_cancelled,
                    )
                    self.processed_files.add(file_path)
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_files)

                self._enqueue_message(
                    "info",
                    (
                        f"Extraction complete. Processed {processed_count} files. "
                        f"Results written to {output_file_name}."
                    ),
                )

        except Exception as exc:
            error_msg = f"Error during extraction: {exc}"
            logger.error(error_msg)
            self._enqueue_message("error", error_msg)
            raise
        else:
            elapsed = perf_counter() - start_time
            files_per_second = (
                processed_count / elapsed if elapsed > 0 else 0.0
            )
            self._last_run_metrics = {
                "processed_files": processed_count,
                "elapsed_seconds": elapsed,
                "files_per_second": files_per_second,
                "max_queue_depth": self._max_queue_depth,
                "total_files": total_files,
            }

            logger.info(
                (
                    "Extraction metrics - processed: %s, elapsed: %.2fs, "
                    "rate: %.2f files/s, max queue depth: %s"
                ),
                processed_count,
                elapsed,
                files_per_second,
                self._max_queue_depth,
            )

            self._enqueue_message(
                "info",
                (
                    "Extraction metrics: "
                    f"processed={processed_count}, elapsed={elapsed:.2f}s, "
                    f"rate={files_per_second:.2f} files/s, "
                    f"max_queue_depth={self._max_queue_depth}"
                ),
            )


__all__ = ["ExtractionCancelled", "FileProcessor"]
