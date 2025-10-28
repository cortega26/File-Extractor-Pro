"""File processing logic for File Extractor Pro."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from datetime import datetime
from queue import Empty, Full, Queue
from typing import IO, Any, Callable, Dict, Sequence, Set

from constants import CHUNK_SIZE, SPECIFICATION_FILES
from logging_utils import logger


class ExtractionCancelled(RuntimeError):
    """Raised when an extraction run is cancelled mid-flight."""


class FileProcessor:
    """Enhanced file processor with improved error handling and performance."""

    def __init__(self, output_queue: Queue):
        self.output_queue = output_queue
        self.extraction_summary: Dict[str, Any] = {}
        self.processed_files: Set[str] = set()
        self._cache: Dict[str, Any] = {}

    def _enqueue_message(self, level: str, message: str) -> None:
        """Safely enqueue status messages without blocking the worker thread."""

        try:
            self.output_queue.put_nowait((level, message))
        except Full:
            try:
                self.output_queue.get_nowait()
            except Empty:
                logger.warning(
                    "Status queue saturated and could not free space for message: %s",
                    message,
                )
                return

            try:
                self.output_queue.put_nowait((level, message))
            except Full:
                logger.warning(
                    "Dropping status message after backpressure attempt: %s", message
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
            if file_size > 100 * 1024 * 1024:
                raise MemoryError(f"File too large to process: {file_path}")

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

        processed_count = 0
        total_files = 0
        seen_paths: Set[str] = set()

        try:
            output_file_abs = os.path.abspath(output_file_name)

            with open(output_file_name, "w", encoding="utf-8") as output:
                self.process_specifications(
                    folder_path,
                    output,
                    is_cancelled=is_cancelled,
                )

                for root, dirs, files in os.walk(folder_path):
                    if is_cancelled and is_cancelled():
                        raise ExtractionCancelled(
                            "Extraction cancelled during traversal"
                        )

                    if not include_hidden:
                        dirs[:] = [
                            directory
                            for directory in dirs
                            if not directory.startswith(".")
                        ]
                        files = [file for file in files if not file.startswith(".")]

                    dirs[:] = [
                        directory
                        for directory in dirs
                        if not any(
                            fnmatch.fnmatch(directory, pattern)
                            for pattern in exclude_folders
                        )
                    ]

                    files = [
                        file
                        for file in files
                        if not any(
                            fnmatch.fnmatch(file, pattern) for pattern in exclude_files
                        )
                    ]

                    for file in files:
                        if is_cancelled and is_cancelled():
                            raise ExtractionCancelled(
                                "Extraction cancelled while iterating files"
                            )

                        file_path = os.path.join(root, file)
                        if os.path.abspath(file_path) == output_file_abs:
                            continue
                        if file_path in self.processed_files or file_path in seen_paths:
                            continue

                        file_ext = os.path.splitext(file)[1]
                        should_process = False
                        if mode == "inclusion":
                            should_process = file_ext in extensions
                        elif mode == "exclusion":
                            should_process = file_ext not in extensions

                        if not should_process:
                            continue

                        seen_paths.add(file_path)
                        total_files += 1

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


__all__ = ["ExtractionCancelled", "FileProcessor"]
