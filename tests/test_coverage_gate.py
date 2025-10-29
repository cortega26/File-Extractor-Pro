"""Tests for the per-file coverage threshold gate."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from tools import coverage_gate


def _write_coverage(tmp_path: Path, xml_body: str) -> Path:
    coverage_xml = tmp_path / "coverage.xml"
    coverage_xml.write_text(dedent(xml_body), encoding="utf-8")
    return coverage_xml


# Fix: testing_ci_coverage_thresholds
def test_evaluate_coverage_flags_under_threshold(tmp_path: Path) -> None:
    report = _write_coverage(
        tmp_path,
        """
        <coverage>
          <packages>
            <package name="services">
              <classes>
                <class name="services.cli" filename="services/cli.py" line-rate="0.92" />
                <class name="processor" filename="processor.py" line-rate="0.81" />
              </classes>
            </package>
          </packages>
        </coverage>
        """,
    )

    failing = coverage_gate.evaluate_coverage(
        coverage_file=report,
        threshold=0.9,
    )

    assert failing == [("processor.py", 0.81)]


# Fix: testing_ci_coverage_thresholds
def test_evaluate_coverage_ignores_prefixes(tmp_path: Path) -> None:
    report = _write_coverage(
        tmp_path,
        """
        <coverage>
          <packages>
            <package name="tests">
              <classes>
                <class name="tests.test_sample" filename="tests/test_sample.py" line-rate="0.5" />
              </classes>
            </package>
          </packages>
        </coverage>
        """,
    )

    failing = coverage_gate.evaluate_coverage(
        coverage_file=report,
        threshold=0.9,
        ignore_prefixes=("tests",),
    )

    assert failing == []


def test_main_returns_error_code_on_failure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = _write_coverage(
        tmp_path,
        """
        <coverage>
          <packages>
            <package name="pkg">
              <classes>
                <class name="pkg.mod" filename="pkg/mod.py" line-rate="0.75" />
              </classes>
            </package>
          </packages>
        </coverage>
        """,
    )

    exit_code = coverage_gate.main([str(report), "--threshold", "0.9"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "pkg/mod.py" in captured.err
