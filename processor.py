"""File processing logic for File Extractor Pro."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from copy import deepcopy
from datetime import datetime
from queue import Empty, Full, Queue
from time import perf_counter
from typing import IO, Any, Callable, Dict, Iterable, MutableMapping, Sequence, Set, Tuple

from constants import CHUNK_SIZE, SPECIFICATION_FILES
from logging_utils import logger


# Fix: Q-105
def _estimate_available_memory_bytes() -> int | None:
    """Best-effort estimate of available address space for soft file limits."""

    # Try process address space limits first (POSIX platforms only).
    try:  # pragma: no cover - resource unavailable on Windows
        import resource

        soft_limit, _ = resource.getrlimit(resource.RLIMIT_AS)
        if soft_limit not in (-1, resource.RLIM_INFINITY) and soft_limit > 0:
            return int(soft_limit)
    except (
        ImportError,
        AttributeError,
        ValueError,
    ):  # pragma: no cover - platform specific
        pass

    # Fallback to sysconf-derived physical memory estimates when available.
    if hasattr(os, "sysconf"):
        try:
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            avail_key = "SC_AVPHYS_PAGES"
            if hasattr(os, "sysconf_names") and avail_key not in os.sysconf_names:
                avail_key = "SC_PHYS_PAGES"
            available_pages = int(os.sysconf(avail_key))
            estimate = page_size * available_pages
            if estimate > 0:
                return int(estimate)
        except (ValueError, OSError, TypeError, AttributeError):
            pass

    return None


class ExtractionCancelled(RuntimeError):
    """Raised when an extraction run is cancelled mid-flight."""


class ExtractionSkipped(RuntimeError):
    """Raised when a file must be skipped for safety reasons."""


class FileProcessor:
    """Enhanced file processor with improved error handling and performance."""

    # Fix: Q-104 - annotate queue payloads for strict type checking support.
    def __init__(
        self,
        output_queue: Queue[Tuple[str, object]],
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
        self._last_run_metrics: Dict[str, float | int | str] = {}
        self._dropped_messages: int = 0
        self._skipped_files: int = 0
        self._large_file_warning_count: int = 0

    # Fix: Q-105
    def configure_max_file_size(self, max_file_size_mb: int | None) -> None:
        """Adjust the soft file size cap used for warning emissions."""

        if max_file_size_mb is None:
            estimated = _estimate_available_memory_bytes()
            self._max_file_size_bytes = (
                estimated if estimated and estimated > 0 else None
            )
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
    def _enqueue_message(self, level: str, message: object) -> None:
        """Safely enqueue status messages without blocking the worker thread."""

        payload: Tuple[str, object] = (level, message)

        def drain_for_capacity(*, allow_state_eviction: bool) -> bool:
            drained_local: list[tuple[str, object]] = []
            while True:
                try:
                    drained_local.append(self.output_queue.get_nowait())
                except Empty:
                    break

            if not drained_local:
                return False

            drop_index: int | None = None
            for index, candidate in enumerate(drained_local):
                if candidate[0] != "state":
                    drop_index = index
                    break

            if drop_index is None:
                if not allow_state_eviction:
                    for restored in drained_local:
                        try:
                            self.output_queue.put_nowait(restored)
                        except Full:
                            logger.warning(
                                "Queue remained saturated while restoring preserved state messages"
                            )
                            self._dropped_messages += 1
                            return False
                        else:
                            self._record_queue_depth()
                    logger.debug(
                        "Skipped dropping state messages to preserve terminal status payloads"
                    )
                    return False
                drop_index = 0

            dropped_message = drained_local.pop(drop_index)
            self._dropped_messages += 1

            for restored in drained_local:
                try:
                    self.output_queue.put_nowait(restored)
                except Full:
                    logger.warning(
                        "Queue remained saturated while restoring drained messages"
                    )
                    self._dropped_messages += 1
                    return False
                else:
                    self._record_queue_depth()

            if dropped_message[0] == "state" and not allow_state_eviction:
                logger.warning("Dropped a state message unexpectedly during backpressure")

            return True

        attempts = 0

        while True:
            try:
                self.output_queue.put_nowait(payload)
                self._record_queue_depth()
                break
            except Full:
                attempts += 1
                allow_state_eviction = level == "state"
                drained = drain_for_capacity(
                    allow_state_eviction=allow_state_eviction
                )
                if not drained and attempts > 1:
                    logger.warning(
                        "Dropping status message after repeated saturation: %s",
                        message,
                    )
                    self._dropped_messages += 1
                    return
                continue

    def process_specifications(
        self,
        directory_path: str,
        output_file: IO[str],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> int:
        """Process specification files first with enhanced error handling."""

        skipped_specs = 0
        for spec_file in SPECIFICATION_FILES:
            if is_cancelled and is_cancelled():
                raise ExtractionCancelled("Extraction cancelled before specs processed")

            try:
                file_path = os.path.join(directory_path, spec_file)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    logger.info("Processing specification file: %s", spec_file)
                    # Fix: Q-105 - respect skip signals emitted from process_file.
                    processed = self.process_file(
                        file_path,
                        output_file,
                        is_cancelled=is_cancelled,
                    )
                    if processed:
                        self.processed_files.add(file_path)
                    else:
                        skipped_specs += 1
            except ExtractionCancelled:
                raise
            except Exception as exc:
                logger.error(
                    "Error processing specification file %s: %s", spec_file, exc
                )
                self._enqueue_message("error", f"Error processing {spec_file}: {exc}")
                skipped_specs += 1
        return skipped_specs

    # Fix: Q-105
    def _stream_file_contents(
        self,
        *,
        file_path: str,
        output_file: IO[str],
        normalized_path: str,
        chunk_size: int,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> str:
        """Stream file contents into the output handle and return the SHA256 hash."""

        sha256 = hashlib.sha256()
        header_written = False

        with open(file_path, "r", encoding="utf-8") as source:
            while True:
                if is_cancelled and is_cancelled():
                    raise ExtractionCancelled(
                        "Extraction cancelled during file processing"
                    )

                chunk = source.read(chunk_size)
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

        return sha256.hexdigest()

    # Fix: Q-105
    def process_file(
        self,
        file_path: str,
        output_file: IO[str],
        *,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> bool:
        """Process individual file with improved error handling and memory management.

        Returns ``True`` when the file contents were streamed successfully and
        ``False`` when the file had to be skipped after emitting error details.
        """

        processed_successfully = False

        can_restore_output = False
        start_position = 0

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
                self._large_file_warning_count += 1

            normalized_path = os.path.normpath(file_path).replace(os.path.sep, "/")
            file_ext = os.path.splitext(file_path)[1]

            can_restore_output = all(
                hasattr(output_file, method) for method in ("tell", "seek", "truncate")
            )
            start_position = output_file.tell() if can_restore_output else 0

            chunk_size = CHUNK_SIZE
            while True:
                try:
                    file_hash = self._stream_file_contents(
                        file_path=file_path,
                        output_file=output_file,
                        normalized_path=normalized_path,
                        chunk_size=chunk_size,
                        is_cancelled=is_cancelled,
                    )
                    processed_successfully = True
                    break
                except MemoryError:
                    if can_restore_output:
                        output_file.seek(start_position)
                        output_file.truncate()

                    next_chunk_size = max(1024, chunk_size // 2)
                    if next_chunk_size == chunk_size:
                        # Fix: Q-105 - skip files that consistently exhaust memory safeguards.
                        logger.error(
                            "Aborting processing for %s after repeated memory errors",
                            file_path,
                        )
                        self._enqueue_message(
                            "error",
                            (
                                "Skipped file due to repeated memory pressure: "
                                f"{file_path}"
                            ),
                        )
                        raise ExtractionSkipped(
                            f"Skipped {file_path} after repeated memory pressure"
                        )

                    logger.warning(
                        "Memory pressure detected while processing %s; retrying with %s-byte chunks",
                        file_path,
                        next_chunk_size,
                    )
                    self._enqueue_message(
                        "warning",
                        (
                            "Memory pressure detected while processing "
                            f"{file_path}; retrying with {next_chunk_size}-byte chunks"
                        ),
                    )
                    chunk_size = next_chunk_size

            self._update_extraction_summary(file_ext, file_path, file_size, file_hash)
            logger.debug("Successfully processed file: %s", file_path)

        except ExtractionCancelled:
            if can_restore_output:
                output_file.seek(start_position)
                output_file.truncate()
            raise
        except ExtractionSkipped:
            if can_restore_output:
                output_file.seek(start_position)
                output_file.truncate()
            raise
        except (UnicodeDecodeError, UnicodeError) as exc:
            if can_restore_output:
                output_file.seek(start_position)
                output_file.truncate()
            logger.warning("Unicode decode error for %s: %s", file_path, exc)
            self._enqueue_message("error", f"Cannot decode file {file_path}: {exc}")
            return False
        except Exception as exc:
            if can_restore_output:
                output_file.seek(start_position)
                output_file.truncate()
            logger.error("Error processing file %s: %s", file_path, exc)
            self._enqueue_message("error", f"Error processing {file_path}: {exc}")
            return False
        return processed_successfully

    @property
    def last_run_metrics(self) -> Dict[str, float | int | str]:
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
        self._dropped_messages = 0
        self._max_queue_depth = 0
        self._last_run_metrics = {}
        # Fix: Q-108 - reset skipped-file counters between runs for accurate metrics.
        self._skipped_files = 0
        self._large_file_warning_count = 0

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
        wildcard_tokens = {"*", "*.*"}
        # Fix: Q-101 - honour wildcard extension tokens for inclusion workflows.
        normalized_extensions = {
            extension.lower()
            for extension in extensions
            if extension not in wildcard_tokens
        }
        has_wildcard = any(extension in wildcard_tokens for extension in extensions)

        for root, dirs, files in os.walk(folder_path):
            if is_cancelled and is_cancelled():
                raise ExtractionCancelled("Extraction cancelled during traversal")

            mutable_dirs = list(dirs)
            mutable_files = list(files)

            if not include_hidden:
                mutable_dirs = [
                    directory
                    for directory in mutable_dirs
                    if not directory.startswith(".")
                ]
                mutable_files = [
                    file_name
                    for file_name in mutable_files
                    if not file_name.startswith(".")
                ]

            filtered_dirs = [
                directory
                for directory in mutable_dirs
                if not any(
                    fnmatch.fnmatch(directory, pattern) for pattern in exclude_folders
                )
            ]
            filtered_files = [
                file_name
                for file_name in mutable_files
                if not any(
                    fnmatch.fnmatch(file_name, pattern) for pattern in exclude_files
                )
            ]

            dirs[:] = filtered_dirs

            for file_name in filtered_files:
                if is_cancelled and is_cancelled():
                    raise ExtractionCancelled(
                        "Extraction cancelled while iterating files"
                    )

                file_path = os.path.join(root, file_name)
                if os.path.abspath(file_path) == output_file_abs:
                    continue
                if file_path in self.processed_files or file_path in seen_paths:
                    continue

                file_ext = os.path.splitext(file_name)[1]
                file_ext_lower = file_ext.lower()
                should_process = False
                if mode == "inclusion":
                    should_process = has_wildcard or (
                        file_ext_lower in normalized_extensions
                    )
                elif mode == "exclusion":
                    if has_wildcard:
                        should_process = False
                    else:
                        should_process = file_ext_lower not in normalized_extensions

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
        self._dropped_messages = 0
        self._large_file_warning_count = 0
        start_time = perf_counter()

        processed_count = 0
        skipped_count = 0

        try:
            output_file_abs = os.path.abspath(output_file_name)

            with open(output_file_name, "w", encoding="utf-8") as output:
                skipped_specs = self.process_specifications(
                    folder_path,
                    output,
                    is_cancelled=is_cancelled,
                )
                skipped_count += skipped_specs

                # Fix: Q-102 - pre-compute eligible files but fall back when memory is scarce.
                total_files: int
                iteration_source: Iterable[str]
                try:
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
                except (MemoryError, OverflowError) as exc:
                    logger.warning(
                        "Falling back to streaming progress estimation due to: %s",
                        exc,
                    )
                    self._enqueue_message(
                        "warning",
                        "Large directory detected; progress will be indeterminate",
                    )
                    total_files = -1
                    iteration_source = self._iter_eligible_file_paths(
                        folder_path=folder_path,
                        mode=mode,
                        include_hidden=include_hidden,
                        extensions=extensions,
                        exclude_files=exclude_files,
                        exclude_folders=exclude_folders,
                        output_file_abs=output_file_abs,
                        is_cancelled=is_cancelled,
                    )
                else:
                    total_files = len(eligible_paths)
                    iteration_source = eligible_paths

                if progress_callback:
                    progress_callback(0, total_files)

                for file_path in iteration_source:
                    try:
                        processed = self.process_file(
                            file_path,
                            output,
                            is_cancelled=is_cancelled,
                        )
                    except ExtractionSkipped as skipped:
                        logger.warning("%s", skipped)
                        skipped_count += 1
                        if progress_callback:
                            # Fix: Q-102 - advance progress when files are skipped.
                            attempts = processed_count + skipped_count
                            progress_callback(attempts, total_files)
                        continue
                    if not processed:
                        skipped_count += 1
                        if progress_callback:
                            # Fix: Q-102 - ensure skipped files still advance progress.
                            attempts = processed_count + skipped_count
                            progress_callback(attempts, total_files)
                        continue
                    self.processed_files.add(file_path)
                    processed_count += 1
                    if progress_callback:
                        progress_callback(processed_count, total_files)

                completion_message = (
                    f"Extraction complete. Processed {processed_count} files. "
                    f"Results written to {output_file_name}."
                )
                if skipped_count:
                    completion_message += (
                        f" Skipped {skipped_count} files due to safeguards."
                    )
                self._enqueue_message("info", completion_message)

        except Exception as exc:
            error_msg = f"Error during extraction: {exc}"
            logger.error(error_msg)
            self._enqueue_message("error", error_msg)
            raise
        else:
            elapsed = perf_counter() - start_time
            files_per_second = processed_count / elapsed if elapsed > 0 else 0.0
            self._skipped_files = skipped_count
            # Fix: Q-108 - normalise instrumentation totals when counts are estimated.
            known_total = total_files if total_files >= 0 else None
            estimated_total = processed_count + skipped_count
            normalised_total = known_total if known_total is not None else estimated_total
            # Fix: Q-102 - finalise determinate progress when totals were estimated.
            if (
                progress_callback
                and known_total is None
                and (processed_count or skipped_count)
            ):
                try:
                    attempts = processed_count + skipped_count
                    progress_callback(attempts, attempts)
                except Exception:  # pragma: no cover - defensive safeguard
                    logger.debug("Progress callback failed to report final totals", exc_info=True)
            self._last_run_metrics = {
                "processed_files": processed_count,
                "elapsed_seconds": elapsed,
                "files_per_second": files_per_second,
                "max_queue_depth": self._max_queue_depth,
                "total_files": normalised_total,
                "dropped_messages": self._dropped_messages,
                "skipped_files": skipped_count,
                "total_files_known": known_total is not None,
                "large_file_warnings": self._large_file_warning_count,
                "max_file_size_bytes": int(self._max_file_size_bytes or 0),
                # Fix: Q-105 - expose large file guard thresholds in human-friendly units.
                "max_file_size_megabytes": round(
                    (self._max_file_size_bytes or 0) / (1024 * 1024), 3
                ),
            }
            if known_total is None:
                self._last_run_metrics["total_files_estimated"] = estimated_total
            # Fix: Q-108 - capture run completion timestamp for telemetry consumers.
            self._last_run_metrics["completed_at"] = datetime.now().isoformat()

            logger.info(
                (
                    "Extraction metrics - processed: %s, elapsed: %.2fs, "
                    "rate: %.2f files/s, max queue depth: %s, skipped: %s"
                ),
                processed_count,
                elapsed,
                files_per_second,
                self._max_queue_depth,
                skipped_count,
            )

            self._enqueue_message(
                "info",
                (
                    "Extraction metrics: "
                    f"processed={processed_count}, elapsed={elapsed:.2f}s, "
                    f"rate={files_per_second:.2f} files/s, "
                    f"max_queue_depth={self._max_queue_depth}, "
                    f"skipped={skipped_count}"
                ),
            )


__all__ = ["ExtractionCancelled", "ExtractionSkipped", "FileProcessor"]
