"""Command-line interface for File Extractor Pro."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Callable, Iterable, Protocol, Sequence, cast

from constants import COMMON_EXTENSIONS
from logging_utils import configure_logging, logger
from processor import FileProcessor
from services.extractor_service import ExtractionRequest, ExtractorService
from services.extension_utils import normalise_extension_tokens


class ThreadLike(Protocol):
    """Minimal protocol representing the worker thread contract."""

    def is_alive(self) -> bool:
        """Return whether the worker is still active."""

    def join(self, timeout: float | None = None) -> None:
        """Block until the worker terminates."""


class ExtractorServiceProtocol(Protocol):
    """Protocol describing the methods used by the CLI runner."""

    output_queue: Queue[tuple[str, object]]

    def start_extraction(
        self,
        *,
        request: ExtractionRequest,
        progress_callback: Callable[[int, int], None],
    ) -> ThreadLike:
        """Start a background extraction task."""

    def is_running(self) -> bool:
        """Return whether a worker is currently active."""

    def cancel(self) -> None:
        """Signal cancellation to the worker."""

    def generate_report(self, *, output_path: str) -> str:
        """Persist the latest extraction report and return the path."""


DEFAULT_POLL_INTERVAL = 0.1


@dataclass(frozen=True)
class CLIOptions:
    """Typed representation of CLI arguments for easier testing."""

    folder_path: Path
    mode: str
    include_hidden: bool
    extensions: tuple[str, ...]
    exclude_files: tuple[str, ...]
    exclude_folders: tuple[str, ...]
    output_file: Path
    report_path: Path | None
    max_file_size_mb: int | None = None
    poll_interval: float = DEFAULT_POLL_INTERVAL
    log_level: str = "INFO"


def _split_csv(values: Iterable[str]) -> tuple[str, ...]:
    """Normalise comma-separated values into a tuple of strings."""

    normalised: list[str] = []
    for value in values:
        for part in value.split(","):
            stripped = part.strip()
            if stripped:
                normalised.append(stripped)
    return tuple(dict.fromkeys(normalised))


# Fix: Q-105
def _positive_int(raw_value: str) -> int:
    """Argparse helper that validates positive integer inputs."""

    try:
        value = int(raw_value)
    except ValueError as exc:  # pragma: no cover - argparse handles messaging
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return value


# Fix: Q-101
def _normalise_extensions(raw_extensions: Iterable[str]) -> tuple[str, ...]:
    """Ensure CLI extensions include a leading dot and deduplicate values."""

    return normalise_extension_tokens(raw_extensions)


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the CLI."""

    parser = argparse.ArgumentParser(description="Run File Extractor Pro headlessly")
    parser.add_argument(
        "folder",
        type=Path,
        help="Folder to extract",
    )
    parser.add_argument(
        "--mode",
        choices=("inclusion", "exclusion"),
        default="inclusion",
        help="Extraction mode (default: inclusion)",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files in traversal",
    )
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=(),
        help=(
            "List of file extensions to include or exclude. "
            "Defaults to common types when omitted in inclusion mode."
        ),
    )
    parser.add_argument(
        "--exclude-files",
        nargs="*",
        default=(),
        help="File name patterns to exclude",
    )
    parser.add_argument(
        "--exclude-folders",
        nargs="*",
        default=(),
        help="Folder name patterns to exclude",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("extraction.txt"),
        help="Output file path (default: extraction.txt)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Optional JSON report path to generate after extraction",
    )
    parser.add_argument(
        "--max-file-size-mb",
        type=_positive_int,
        help=(
            "Optional soft limit for file sizes in megabytes. "
            "Values above the threshold emit warnings but do not abort."
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help="Queue polling interval in seconds (default: 0.1)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        type=str.upper,
        help="Console log level",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> CLIOptions:
    """Parse raw command-line arguments into a :class:`CLIOptions`."""

    parser = build_parser()
    args = parser.parse_args(argv)

    raw_extensions = _split_csv(args.extensions)
    extensions = _normalise_extensions(raw_extensions)
    if args.mode == "inclusion" and not extensions:
        extensions = tuple(COMMON_EXTENSIONS)
    exclude_files = _split_csv(args.exclude_files)
    exclude_folders = _split_csv(args.exclude_folders)

    return CLIOptions(
        folder_path=args.folder,
        mode=args.mode,
        include_hidden=args.include_hidden,
        extensions=extensions,
        exclude_files=exclude_files,
        exclude_folders=exclude_folders,
        output_file=args.output,
        report_path=args.report,
        max_file_size_mb=args.max_file_size_mb,
        poll_interval=args.poll_interval,
        log_level=args.log_level,
    )


def _drain_queue_messages(
    service: ExtractorServiceProtocol,
) -> list[tuple[str, object]]:
    """Drain available queue messages for processing."""

    drained: list[tuple[str, object]] = []
    while True:
        try:
            drained.append(service.output_queue.get_nowait())
        except Empty:
            break
    return drained


def _log_queue_messages(messages: Iterable[tuple[str, object]]) -> str | None:
    """Log queue messages and return the final state result if present."""

    final_result: str | None = None
    for level, payload in messages:
        if level == "state" and isinstance(payload, dict):
            result = str(payload.get("result", ""))
            final_result = result or final_result
            logger.info("Extraction finished with state: %s", result or "unknown")
            continue
        if isinstance(payload, dict):
            logger.info("%s", payload)
            continue
        log_method: Callable[[str], None]
        if level == "error":
            log_method = logger.error
            if final_result is None:
                final_result = "error"
        elif level == "warning":
            log_method = logger.warning
        else:
            log_method = logger.info
        log_method(str(payload))
    return final_result


def _progress_callback(processed: int, total: int) -> None:
    """Default progress callback used by the CLI."""

    if total <= 0:
        logger.info("Processed %s files", processed)
        return
    # Fix: Q-102 - prevent progress percentages from exceeding 100%.
    safe_processed = min(processed, total)
    percent = (safe_processed / total) * 100
    logger.info("Progress: %.1f%% (%s/%s)", percent, processed, total)


def run_cli(
    options: CLIOptions,
    *,
    service_factory: Callable[..., ExtractorServiceProtocol] = ExtractorService,
    configure_logger_handler: bool = True,
) -> int:
    """Execute the extraction using the service layer and return an exit code."""

    if configure_logger_handler and not logger.handlers:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        configure_logging(
            handler=stream_handler,
            level=getattr(logging, options.log_level.upper(), logging.INFO),
        )
    else:
        logger.setLevel(getattr(logging, options.log_level.upper(), logging.INFO))

    # Fix: Q-101 - guard manual invocations that omit extensions in inclusion mode.
    if options.mode == "inclusion" and not options.extensions:
        logger.debug(
            "No extensions provided for inclusion run; defaulting to COMMON_EXTENSIONS"
        )
        options = replace(options, extensions=tuple(COMMON_EXTENSIONS))

    # Fix: Q-105 - allow CLI callers to configure the soft file size cap.
    # Fix: Q-104 - ensure strict typing of injected processor factories.
    processor_factory: Callable[[Queue[tuple[str, object]]], FileProcessor] | None = None
    service_kwargs: dict[str, object] = {}
    if options.max_file_size_mb is not None:

        def processor_factory(output_queue: Queue[tuple[str, object]]) -> FileProcessor:
            return FileProcessor(
                output_queue,
                max_file_size_mb=options.max_file_size_mb,
            )

        service_kwargs["file_processor_factory"] = processor_factory

    try:
        service = service_factory(**service_kwargs)
    except TypeError as exc:
        if not service_kwargs:
            raise
        logger.debug(
            "Service factory rejected file_processor_factory override: %s", exc
        )
        service = service_factory()
        file_processor = cast(Any, getattr(service, "file_processor", None))
        if file_processor is not None and hasattr(
            file_processor, "configure_max_file_size"
        ):
            file_processor.configure_max_file_size(options.max_file_size_mb)
    request = ExtractionRequest(
        folder_path=str(options.folder_path),
        mode=options.mode,
        include_hidden=options.include_hidden,
        extensions=tuple(options.extensions),
        exclude_files=tuple(options.exclude_files),
        exclude_folders=tuple(options.exclude_folders),
        output_file_name=str(options.output_file),
    )
    thread = service.start_extraction(
        request=request,
        progress_callback=_progress_callback,
    )

    final_result: str | None = None
    try:
        while thread.is_alive():
            time.sleep(options.poll_interval)
            messages = _drain_queue_messages(service)
            result = _log_queue_messages(messages)
            if result:
                final_result = result
        thread.join()
        result = _log_queue_messages(_drain_queue_messages(service))
        if result:
            final_result = result
    finally:
        if service.is_running():
            service.cancel()

    # Fix: Q-108 - surface instrumentation metrics even if queue messages were dropped.
    processor = getattr(service, "file_processor", None)
    if processor is not None:
        metrics: dict[str, float | int] | None = None
        try:
            metrics = getattr(processor, "last_run_metrics", None)
            if callable(metrics):  # pragma: no cover - defensive branch
                metrics = metrics()
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.debug("Unable to access processor metrics: %s", exc)
        else:
            if metrics:
                processed = metrics.get("processed_files", 0)
                elapsed = float(metrics.get("elapsed_seconds", 0.0))
                rate = float(metrics.get("files_per_second", 0.0))
                queue_depth = metrics.get("max_queue_depth", 0)
                total_files = metrics.get("total_files", processed)
                dropped_messages = metrics.get("dropped_messages", 0)
                skipped_files = metrics.get("skipped_files", 0)
                logger.info(
                    (
                        "Extraction metrics summary: processed=%s, total=%s, "
                        "elapsed=%.2fs, rate=%.2f files/s, max_queue_depth=%s, "
                        "dropped_messages=%s, skipped=%s"
                    ),
                    processed,
                    total_files,
                    elapsed,
                    rate,
                    queue_depth,
                    dropped_messages,
                    skipped_files,
                )

    if options.report_path:
        try:
            service.generate_report(output_path=str(options.report_path))
        except ValueError as exc:
            logger.warning("Skipping report generation: %s", exc)

    # Fix: Q-106 - fall back to the last known state payload if queue delivery failed.
    if final_result is None:
        last_state_getter = getattr(service, "get_last_state_payload", None)
        if callable(last_state_getter):
            last_state = last_state_getter() or {}
            final_result = str(last_state.get("result")) or None

    if final_result == "error":
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by ``python -m services.cli``."""

    options = parse_arguments(argv)
    try:
        return run_cli(options)
    except KeyboardInterrupt:
        logger.warning("Extraction interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
