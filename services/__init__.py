"""Service layer abstractions for File Extractor Pro."""

from .cli import CLIOptions, build_parser
from .cli import main as cli_main
from .cli import parse_arguments, run_cli
from .extractor_service import ExtractionSummary, ExtractorService

__all__ = [
    "CLIOptions",
    "ExtractorService",
    "ExtractionSummary",
    "build_parser",
    "cli_main",
    "parse_arguments",
    "run_cli",
]
