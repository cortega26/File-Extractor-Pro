"""Utility for running the mandated security scanners in sequence."""

from __future__ import annotations

import argparse
import subprocess
from typing import Iterable, List, Sequence

Command = Sequence[str]


_DEFAULT_COMMANDS: tuple[Command, ...] = (
    ("bandit", "-ll", "-q", "-r", "."),
    ("pip-audit",),
    ("gitleaks", "detect", "--redact"),
)


# Fix: testing_ci_security_scanners
def build_security_commands(skipped: Sequence[str] | None = None) -> List[List[str]]:
    """Return the security command matrix with optional exclusions."""

    skip = {tool.lower() for tool in (skipped or [])}
    return [list(command) for command in _DEFAULT_COMMANDS if command[0] not in skip]


# Fix: testing_ci_security_scanners
def run_security_checks(commands: Iterable[Command]) -> int:
    """Execute the configured security commands sequentially."""

    for command in commands:
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run File Extractor Pro security scanners in order",
    )
    parser.add_argument(
        "--skip",
        action="append",
        choices=["bandit", "pip-audit", "gitleaks"],
        default=[],
        help="Skip the specified scanner (may be provided multiple times)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by CI to invoke all security tooling."""

    args = _parse_args(argv)
    commands = build_security_commands(args.skip)
    if not commands:
        return 0
    return run_security_checks(commands)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

