"""Tests for the security check orchestration helper."""

from __future__ import annotations

from typing import Iterable, Sequence
from unittest.mock import Mock

import pytest

from tools import security_checks


# Fix: testing_ci_security_scanners
def test_build_security_commands_respects_skip_filter() -> None:
    commands = security_checks.build_security_commands(["bandit", "pip-audit"])
    assert commands == [["gitleaks", "detect", "--redact"]]


# Fix: testing_ci_security_scanners
def test_run_security_checks_stops_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Sequence[str]] = []

    def fake_run(command: Sequence[str], check: bool = False) -> Mock:  # type: ignore[override]
        calls.append(tuple(command))
        mock_result = Mock()
        mock_result.returncode = 1 if command[0] == "pip-audit" else 0
        return mock_result

    monkeypatch.setattr(security_checks.subprocess, "run", fake_run)
    result = security_checks.run_security_checks(security_checks._DEFAULT_COMMANDS)

    assert result == 1
    assert calls[:2] == [security_checks._DEFAULT_COMMANDS[0], security_checks._DEFAULT_COMMANDS[1]]


def test_main_honours_skip_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[Iterable[str]] = []

    def fake_run(command: Sequence[str], check: bool = False) -> Mock:  # type: ignore[override]
        recorded.append(command)
        mock_result = Mock()
        mock_result.returncode = 0
        return mock_result

    monkeypatch.setattr(security_checks.subprocess, "run", fake_run)
    exit_code = security_checks.main(["--skip", "bandit"])

    assert exit_code == 0
    assert [cmd[0] for cmd in recorded] == ["pip-audit", "gitleaks"]

