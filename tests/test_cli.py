"""Tests for the command-line interface."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from queue import Queue

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from constants import COMMON_EXTENSIONS
from services.cli import CLIOptions, parse_arguments, run_cli
from services.extractor_service import ExtractionRequest

logger = logging.getLogger("file_extractor")


class FakeThread:
    """Minimal thread stand-in used for CLI tests."""

    def __init__(self) -> None:
        self._alive = True

    def is_alive(self) -> bool:
        if self._alive:
            self._alive = False
            return True
        return False

    def join(
        self, timeout: float | None = None
    ) -> None:  # noqa: ARG002 - interface match
        self._alive = False


class SuccessfulService:
    """Service double that simulates a successful extraction run."""

    def __init__(self) -> None:
        self.output_queue: Queue[tuple[str, object]] = Queue()
        self.generated_report: str | None = None
        self.received_arguments: dict[str, object] | None = None

    def start_extraction(
        self,
        *,
        request: ExtractionRequest,
        progress_callback,
    ) -> FakeThread:
        extensions = list(request.extensions)
        self.received_arguments = {
            "folder_path": request.folder_path,
            "mode": request.mode,
            "include_hidden": request.include_hidden,
            "extensions": extensions,
            "exclude_files": list(request.exclude_files),
            "exclude_folders": list(request.exclude_folders),
            "output_file_name": request.output_file_name,
        }
        progress_callback(1, max(1, len(extensions)))
        self.output_queue.put(("info", "Extraction complete. Processed 1 files."))
        self.output_queue.put(("state", {"status": "finished", "result": "success"}))
        return FakeThread()

    def is_running(self) -> bool:
        return False

    def generate_report(self, *, output_path: str) -> str:
        self.generated_report = output_path
        return output_path

    def cancel(self) -> None:
        return None


class ErrorService(SuccessfulService):
    """Service double that yields an error state."""

    def start_extraction(self, *args, **kwargs):  # type: ignore[override]
        thread = super().start_extraction(*args, **kwargs)
        self.output_queue.put(("error", "Unexpected failure"))
        self.output_queue.put(("state", {"status": "finished", "result": "error"}))
        return thread


def test_parse_arguments_normalises_values(tmp_path: Path) -> None:
    options = parse_arguments(
        [
            str(tmp_path),
            "--mode",
            "exclusion",
            "--include-hidden",
            "--extensions",
            "txt",
            "md",
            ",py",
            "--exclude-files",
            "*.tmp",
            ".DS_Store",
            "--exclude-folders",
            "__pycache__",
            "build",
            "--output",
            str(tmp_path / "output.txt"),
            "--report",
            str(tmp_path / "report.json"),
            "--poll-interval",
            "0.0",
            "--log-level",
            "debug",
        ]
    )

    assert options.mode == "exclusion"
    assert options.include_hidden is True
    assert options.extensions == ("txt", "md", "py")
    assert options.exclude_files == ("*.tmp", ".DS_Store")
    assert options.exclude_folders == ("__pycache__", "build")
    assert options.output_file.name == "output.txt"
    assert options.report_path and options.report_path.name == "report.json"
    assert options.poll_interval == 0.0
    assert options.log_level == "DEBUG"


def test_parse_arguments_defaults_extensions_for_inclusion(tmp_path: Path) -> None:
    options = parse_arguments([str(tmp_path)])

    assert options.mode == "inclusion"
    assert options.extensions == tuple(COMMON_EXTENSIONS)


def test_run_cli_success(caplog, tmp_path: Path) -> None:
    options = CLIOptions(
        folder_path=tmp_path,
        mode="inclusion",
        include_hidden=False,
        extensions=("txt",),
        exclude_files=(),
        exclude_folders=(),
        output_file=tmp_path / "out.txt",
        report_path=tmp_path / "report.json",
        poll_interval=0.0,
        log_level="INFO",
    )

    original_handlers = list(logger.handlers)
    original_propagate = logger.propagate
    original_level = logger.level

    caplog.set_level(logging.INFO, logger="file_extractor")
    logger.handlers.clear()
    logger.propagate = True

    service_instance: SuccessfulService | None = None

    def service_factory() -> SuccessfulService:
        nonlocal service_instance
        service_instance = SuccessfulService()
        return service_instance

    try:
        exit_code = run_cli(
            options,
            service_factory=service_factory,
            configure_logger_handler=False,
        )

        assert exit_code == 0
        assert service_instance is not None
        assert service_instance.generated_report == str(options.report_path)
        assert service_instance.received_arguments is not None
        assert service_instance.received_arguments["folder_path"] == str(tmp_path)
        assert any(
            "Extraction finished with state" in message for message in caplog.messages
        )
    finally:
        logger.handlers[:] = original_handlers
        logger.propagate = original_propagate
        logger.setLevel(original_level)


def test_run_cli_returns_error_on_failure(caplog, tmp_path: Path) -> None:
    options = CLIOptions(
        folder_path=tmp_path,
        mode="inclusion",
        include_hidden=False,
        extensions=(),
        exclude_files=(),
        exclude_folders=(),
        output_file=tmp_path / "out.txt",
        report_path=None,
        poll_interval=0.0,
        log_level="INFO",
    )

    original_handlers = list(logger.handlers)
    original_propagate = logger.propagate
    original_level = logger.level

    caplog.set_level(logging.INFO, logger="file_extractor")
    logger.handlers.clear()
    logger.propagate = True

    try:
        exit_code = run_cli(
            options,
            service_factory=ErrorService,
            configure_logger_handler=False,
        )

        assert exit_code == 1
        assert any("Unexpected failure" in message for message in caplog.messages)
    finally:
        logger.handlers[:] = original_handlers
        logger.propagate = original_propagate
        logger.setLevel(original_level)
