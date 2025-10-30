"""Regression tests for declared tooling dependencies."""

from __future__ import annotations

from pathlib import Path


# Fix: testing_ci_coverage_plugin
def test_pytest_cov_listed_in_runtime_requirements() -> None:
    """pytest-cov must ship with the runtime requirements for CI coverage gates."""

    requirements_path = Path(__file__).resolve().parents[1] / "requirements.txt"
    contents = requirements_path.read_text(encoding="utf-8").splitlines()

    assert any(line.startswith("pytest-cov") for line in contents)


# Fix: Q-110
def test_coverage_fail_under_threshold() -> None:
    """Coverage configuration must enforce the documented minimum threshold."""

    import tomllib

    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    fail_under = data["tool"]["coverage"]["report"]["fail_under"]

    assert fail_under >= 80
