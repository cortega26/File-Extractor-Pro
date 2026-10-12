"""Regression tests for zero-write previews and matching extraction selection."""

from __future__ import annotations

import json
import os
from pathlib import Path
from queue import Queue

import pytest

from processor import FileProcessor
from services.cli import main
from services.preview import build_preview, format_preview


def _preview(root: Path, output: Path, **changes):
    args = {
        "folder_path": root,
        "mode": "inclusion",
        "include_hidden": False,
        "extensions": (".md", ".py"),
        "exclude_files": (),
        "exclude_folders": (),
        "output_file": output,
    }
    args.update(changes)
    return build_preview(**args)


def test_preview_lists_stable_order_and_size_without_writing(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "z.py").write_text("z", encoding="utf-8")
    (tmp_path / "src" / "a.py").write_text("abc", encoding="utf-8")
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    out = tmp_path / "bundle.txt"
    first = _preview(tmp_path, out)
    second = _preview(tmp_path, out)

    assert first == second
    assert [e["path"] for e in first["files"]] == [
        "README.md", "src/a.py", "src/z.py"
    ]
    assert first["total_bytes"] == 10
    assert not out.exists()
    assert json.loads(format_preview(first, "json")) == first


def test_preview_matches_extractor_when_readme_is_excluded(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("SHOULD-NOT-BE-EXPORTED", encoding="utf-8")
    (tmp_path / "source.py").write_text("print('ok')", encoding="utf-8")
    out = tmp_path / "bundle.txt"
    selected = _preview(tmp_path, out, extensions=(".py",), exclude_files=("README.md",))
    assert [e["path"] for e in selected["files"]] == ["source.py"]

    processor = FileProcessor(Queue())
    processor.extract_files(
        folder_path=str(tmp_path),
        mode="inclusion",
        include_hidden=False,
        extensions=(".py",),
        exclude_files=("README.md",),
        exclude_folders=(),
        output_file_name=str(out),
    )
    extracted = out.read_text(encoding="utf-8")
    assert "SHOULD-NOT-BE-EXPORTED" not in extracted
    assert "print('ok')" in extracted


def test_cli_dry_run_json_is_read_only(tmp_path: Path, capsys) -> None:
    (tmp_path / "file.py").write_text("test", encoding="utf-8")
    out = tmp_path / "output.txt"
    report = tmp_path / "report.json"
    code = main([
        str(tmp_path),
        "--extensions", "py",
        "--dry-run",
        "--preview-format", "json",
        "--output", str(out),
        "--report", str(report),
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["file_count"] == 1
    assert payload["files"][0]["path"] == "file.py"
    assert not out.exists()
    assert not report.exists()


def test_preview_never_mutates_existing_output(tmp_path: Path) -> None:
    (tmp_path / "source.py").write_text("secret", encoding="utf-8")
    out = tmp_path / "bundle.txt"
    out.write_text("keep-me", encoding="utf-8")
    preview = _preview(tmp_path, out)
    assert preview["file_count"] == 1
    assert preview["warnings"]
    assert out.read_text(encoding="utf-8") == "keep-me"


def test_file_symlink_outside_tree_is_excluded(tmp_path: Path) -> None:
    outside = tmp_path.parent / (tmp_path.name + "-outside.py")
    outside.write_text("outside", encoding="utf-8")
    link = tmp_path / "link.py"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks are unavailable")
    try:
        result = _preview(tmp_path, tmp_path / "out.txt", extensions=(".py",))
        assert result["file_count"] == 0
    finally:
        link.unlink()
        outside.unlink()


def test_preview_invalid_folder_returns_error(tmp_path: Path, capsys) -> None:
    code = main([str(tmp_path / "missing"), "--dry-run"])
    assert code == 1
    assert "Preview failed:" in capsys.readouterr().err


def test_preview_rejects_invalid_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        format_preview(_preview(tmp_path, tmp_path / "out.txt"), "xml")
