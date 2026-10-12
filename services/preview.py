"""Read-only, deterministic preview of a proposed extraction run.

Both preview and extraction use FileProcessor._iter_eligible_file_paths so that
there are no independent, diverging file-selection implementations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from queue import Queue
from typing import Any, Sequence

from constants import COMMON_EXTENSIONS
from processor import FileProcessor


def build_preview(
    *,
    folder_path: Path,
    mode: str,
    include_hidden: bool,
    extensions: Sequence[str],
    exclude_files: Sequence[str],
    exclude_folders: Sequence[str],
    output_file: Path,
) -> dict[str, Any]:
    """Produce an exact file-selection plan without creating or modifying files."""
    root = folder_path.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    normalized_mode = mode.lower()
    if normalized_mode not in {"inclusion", "exclusion"}:
        raise ValueError(f"Unsupported extraction mode: {mode}")

    selected_extensions = (
        tuple(COMMON_EXTENSIONS)
        if normalized_mode == "inclusion" and not extensions
        else tuple(extensions)
    )
    processor = FileProcessor(Queue())
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    output_abs = os.path.abspath(output_file)

    for file_path in processor._iter_eligible_file_paths(
        folder_path=str(root),
        mode=normalized_mode,
        include_hidden=include_hidden,
        extensions=selected_extensions,
        exclude_files=exclude_files,
        exclude_folders=exclude_folders,
        output_file_abs=output_abs,
    ):
        try:
            size = os.path.getsize(file_path)
        except OSError as exc:
            warnings.append(f"Could not stat {file_path}: {exc}")
            continue
        entries.append(
            {
                "path": Path(file_path).relative_to(root).as_posix(),
                "size_bytes": size,
            }
        )

    if output_file.exists():
        warnings.append(f"Extraction will overwrite existing output: {output_file}")

    total_bytes = sum(entry["size_bytes"] for entry in entries)
    return {
        "source": str(root),
        "output": str(output_file),
        "mode": normalized_mode,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "files": entries,
        "warnings": warnings,
        "note": (
            "Preview reports selection and source sizes; unreadable or non-UTF-8 "
            "files may be skipped during extraction."
        ),
    }


def format_preview(preview: dict[str, Any], format_name: str = "text") -> str:
    """Render the preview as readable terminal text or machine-readable JSON."""
    if format_name == "json":
        return json.dumps(preview, indent=2, ensure_ascii=False)
    if format_name != "text":
        raise ValueError(f"Unsupported preview format: {format_name}")

    lines = [
        "File Extractor Pro — read-only preview",
        f"Source: {preview['source']}",
        f"Output: {preview['output']}",
        f"Selected: {preview['file_count']} files, "
        f"{preview['total_bytes']} source bytes",
        "",
    ]
    for entry in preview["files"]:
        lines.append(f"  {entry['path']}  ({entry['size_bytes']} bytes)")
    if preview["warnings"]:
        lines.extend(["", "Warnings:"])
        lines.extend(f"  - {warning}" for warning in preview["warnings"])
    lines.extend(["", str(preview["note"])])
    return "\n".join(lines)


__all__ = ["build_preview", "format_preview"]
