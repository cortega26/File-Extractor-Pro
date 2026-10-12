"""Regression tests for declared tooling dependencies."""

from __future__ import annotations

from pathlib import Path


def test_coverage_tooling_is_development_only() -> None:
    """Runtime stays stdlib-only; pytest-cov belongs to dev requirements."""
    root = Path(__file__).resolve().parents[1]
    runtime = (root / "requirements.txt").read_text(encoding="utf-8").splitlines()
    development = (
        (root / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
    )
    assert not any(line.startswith("pytest-cov") for line in runtime)
    assert any(line.startswith("pytest-cov") for line in development)


def test_installable_distribution_declares_both_entry_points() -> None:
    """The packaged CLI and GUI must remain available as installed commands."""
    import tomllib

    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "file-extractor-pro"
    assert project["dependencies"] == []
    assert project["scripts"]["file-extractor-pro"] == "services.cli:main"
    assert (
        project["gui-scripts"]["file-extractor-pro-gui"]
        == "file_extractor:main"
    )
    assert {"services", "ui_support"} <= set(data["tool"]["setuptools"]["packages"])


# Fix: Q-110
def test_coverage_fail_under_threshold() -> None:
    """Coverage configuration must enforce the documented minimum threshold."""

    import tomllib

    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    fail_under = data["tool"]["coverage"]["report"]["fail_under"]

    assert fail_under >= 80
