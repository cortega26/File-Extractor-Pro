"""File processing logic for File Extractor Pro."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from datetime import datetime
from queue import Empty, Full, Queue
from typing import Any, Awaitable, Callable, Dict, Sequence, Set

import aiofiles

from constants import CHUNK_SIZE, SPECIFICATION_FILES
from logging_utils import logger


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

    async def process_specifications(
        self, directory_path: str, output_file: Any
    ) -> None:
        """Process specification files first with enhanced error handling."""
        for spec_file in SPECIFICATION_FILES:
            try:
                file_path = os.path.join(directory_path, spec_file)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    logger.info("Processing specification file: %s", spec_file)
                    await self.process_file(file_path, output_file)
                    self.processed_files.add(file_path)
            except Exception as exc:
                logger.error(
                    "Error processing specification file %s: %s", spec_file, exc
                )
                self._enqueue_message("error", f"Error processing {spec_file}: {exc}")

    async def process_file(self, file_path: str, output_file: Any) -> None:
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
                start_position = await output_file.tell()

            try:
                header_written = False

                async with aiofiles.open(file_path, "r", encoding="utf-8") as source:
                    while True:
                        chunk = await source.read(CHUNK_SIZE)
                        if not chunk:
                            break

                        if not header_written:
                            await output_file.write(f"{normalized_path}:\n")
                            header_written = True

                        sha256.update(chunk.encode("utf-8"))
                        await output_file.write(chunk)

                if not header_written:
                    await output_file.write(f"{normalized_path}:\n")

                await output_file.write("\n\n\n")

            except Exception:
                if can_restore_output:
                    await output_file.seek(start_position)
                    await output_file.truncate()
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

    async def extract_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: Sequence[str],
        exclude_files: Sequence[str],
        exclude_folders: Sequence[str],
        output_file_name: str,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        """Extract files with improved error handling and progress reporting."""

        processed_count = 0
        total_files = 0
        seen_paths: Set[str] = set()

        try:
            output_file_abs = os.path.abspath(output_file_name)

            async with aiofiles.open(output_file_name, "w", encoding="utf-8") as output:
                await self.process_specifications(folder_path, output)

                for root, dirs, files in os.walk(folder_path):
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

                        await self.process_file(file_path, output)
                        self.processed_files.add(file_path)
                        processed_count += 1
                        await progress_callback(processed_count, total_files)

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


__all__ = ["FileProcessor"]
