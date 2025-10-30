"""CLI for enforcing strict mypy runs in CI."""

from __future__ import annotations

import argparse
import subprocess
from typing import Sequence


DEFAULT_TARGETS: tuple[str, ...] = (".",)


# Fix: testing_ci_strict_typechecking
def build_mypy_command(paths: Sequence[str] | None = None) -> list[str]:
    """Construct the mypy command line for strict type checking."""

    targets = list(paths or DEFAULT_TARGETS)
    if not targets:
        targets = list(DEFAULT_TARGETS)
    return ["mypy", "--strict", *targets]


# Fix: testing_ci_strict_typechecking
def run_typecheck(command: Sequence[str]) -> int:
    """Execute mypy and return its exit status."""

    completed = subprocess.run(command, check=False)
    return completed.returncode


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run mypy --strict against the provided targets",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=list(DEFAULT_TARGETS),
        help="One or more filesystem targets to type check (default: current directory)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for CI environments enforcing strict type checking."""

    args = _parse_args(argv)
    command = build_mypy_command(args.paths)
    return run_typecheck(command)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

