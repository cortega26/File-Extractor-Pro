"""Unit tests for the strict type-checking gate utility."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Sequence

import pytest

from tools import typecheck_gate
from tools.typecheck_gate import build_mypy_command, run_typecheck


# Fix: testing_ci_strict_typechecking
def test_build_mypy_command_defaults_to_current_directory() -> None:
    """Default invocation should target the repository root."""

    command = build_mypy_command()
    assert command == ["mypy", "--strict", "."]


# Fix: testing_ci_strict_typechecking
def test_build_mypy_command_accepts_custom_paths() -> None:
    """Caller-specified targets should be appended to the command."""

    command = build_mypy_command(["services", "processor.py"])
    assert command == ["mypy", "--strict", "services", "processor.py"]


# Fix: testing_ci_strict_typechecking
def test_run_typecheck_propagates_return_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """The helper should surface mypy's exit status."""

    captured: dict[str, Sequence[str]] = {}

    def fake_run(command: Sequence[str], check: bool) -> SimpleNamespace:  # type: ignore[override]
        captured["command"] = list(command)
        assert not check
        return SimpleNamespace(returncode=3)

    monkeypatch.setattr("subprocess.run", fake_run)

    result = run_typecheck(["mypy", "--strict", "services"])
    assert result == 3
    assert captured["command"] == ["mypy", "--strict", "services"]


# Fix: testing_ci_strict_typechecking
def test_main_invokes_typecheck_with_parsed_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI should translate CLI arguments into a strict mypy run."""

    recorded: dict[str, list[str]] = {}

    def fake_run(command: list[str]) -> int:
        recorded["command"] = command
        return 0

    monkeypatch.setattr(typecheck_gate, "run_typecheck", fake_run)

    exit_code = typecheck_gate.main(["services", "tests"])
    assert exit_code == 0
    assert recorded["command"] == ["mypy", "--strict", "services", "tests"]

