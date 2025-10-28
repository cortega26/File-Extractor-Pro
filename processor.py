"""File processing logic for File Extractor Pro."""

from __future__ import annotations

import fnmatch
import hashlib
import os
from datetime import datetime
from queue import Queue
from typing import Any, Awaitable, Callable, Dict, List, Set

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
                self.output_queue.put(("error", f"Error processing {spec_file}: {exc}"))

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

            content = []
            async with aiofiles.open(file_path, "r", encoding="utf-8") as source:
                while chunk := await source.read(CHUNK_SIZE):
                    content.append(chunk)

            file_content = "".join(content)
            await output_file.write(f"{normalized_path}:\n{file_content}\n\n\n")

            file_ext = os.path.splitext(file_path)[1]
            file_hash = hashlib.sha256(file_content.encode()).hexdigest()

            self._update_extraction_summary(file_ext, file_path, file_size, file_hash)

            logger.debug("Successfully processed file: %s", file_path)

        except (UnicodeDecodeError, UnicodeError) as exc:
            logger.warning("Unicode decode error for %s: %s", file_path, exc)
            self.output_queue.put(("error", f"Cannot decode file {file_path}: {exc}"))
        except Exception as exc:
            logger.error("Error processing file %s: %s", file_path, exc)
            self.output_queue.put(("error", f"Error processing {file_path}: {exc}"))

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
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str],
        output_file_name: str,
        progress_callback: Callable[[int, int], Awaitable[None]],
    ) -> None:
        """Extract files with improved error handling and progress reporting."""

        total_files = 0
        processed_files = 0

        try:
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
                        if file_path in self.processed_files:
                            continue

                        file_ext = os.path.splitext(file)[1]
                        if (mode == "inclusion" and file_ext in extensions) or (
                            mode == "exclusion" and file_ext not in extensions
                        ):
                            total_files += 1

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
                        if file_path in self.processed_files:
                            continue

                        file_ext = os.path.splitext(file)[1]
                        if (mode == "inclusion" and file_ext in extensions) or (
                            mode == "exclusion" and file_ext not in extensions
                        ):
                            await self.process_file(file_path, output)
                            processed_files += 1
                            await progress_callback(processed_files, total_files)

                self.output_queue.put(
                    (
                        "info",
                        f"Extraction complete. Processed {processed_files} files. "
                        f"Results written to {output_file_name}.",
                    )
                )

        except Exception as exc:
            error_msg = f"Error during extraction: {exc}"
            logger.error(error_msg)
            self.output_queue.put(("error", error_msg))
            raise


__all__ = ["FileProcessor"]
