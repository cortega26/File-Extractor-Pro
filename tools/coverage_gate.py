"""Enforce per-file coverage thresholds from coverage.py XML reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Sequence
from xml.etree import ElementTree as ET


DEFAULT_THRESHOLD = 0.9


# Fix: testing_ci_coverage_thresholds
def _iter_class_nodes(tree: ET.ElementTree) -> Iterable[ET.Element]:
    """Yield coverage ``class`` nodes from the parsed XML tree."""

    root = tree.getroot()
    for class_node in root.findall(".//class"):
        if class_node.get("filename"):
            yield class_node


# Fix: testing_ci_coverage_thresholds
def _normalise_path(filename: str) -> str:
    """Convert coverage filenames to normalised POSIX-style paths."""

    return filename.replace("\\", "/")


# Fix: testing_ci_coverage_thresholds
def evaluate_coverage(
    *,
    coverage_file: Path,
    threshold: float = DEFAULT_THRESHOLD,
    ignore_prefixes: Sequence[str] = (),
) -> list[tuple[str, float]]:
    """Return files whose line coverage falls below the configured threshold."""

    if threshold <= 0 or threshold > 1:
        raise ValueError("threshold must be within (0, 1]")

    try:
        tree = ET.parse(coverage_file)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid coverage XML: {exc}") from exc

    failing: list[tuple[str, float]] = []
    normalised_prefixes = tuple(prefix.rstrip("/") + "/" for prefix in ignore_prefixes)

    for class_node in _iter_class_nodes(tree):
        raw_filename = class_node.get("filename", "")
        filename = _normalise_path(raw_filename)
        if any(filename.startswith(prefix) for prefix in normalised_prefixes):
            continue

        try:
            line_rate = float(class_node.get("line-rate", "0"))
        except ValueError:
            line_rate = 0.0

        if line_rate + 1e-9 < threshold:
            failing.append((filename, line_rate))

    return failing


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate per-file coverage thresholds using coverage XML reports",
    )
    parser.add_argument(
        "coverage_file",
        type=Path,
        nargs="?",
        default=Path("coverage.xml"),
        help="Path to the coverage XML report (default: coverage.xml)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help="Minimum per-file line coverage percentage expressed as a decimal",
    )
    parser.add_argument(
        "--ignore-prefix",
        action="append",
        default=[],
        help="Skip files whose normalised path starts with the provided prefix",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point used by CI to enforce per-file coverage thresholds."""

    args = _parse_args(argv)

    coverage_path: Path = args.coverage_file
    if not coverage_path.exists():
        print(f"Coverage file not found: {coverage_path}", file=sys.stderr)
        return 2

    failing = evaluate_coverage(
        coverage_file=coverage_path,
        threshold=args.threshold,
        ignore_prefixes=tuple(args.ignore_prefix),
    )

    if not failing:
        return 0

    print("Per-file coverage violations detected:", file=sys.stderr)
    for filename, line_rate in failing:
        percentage = line_rate * 100
        print(f" - {filename}: {percentage:.2f}%", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

