# File Extractor Pro

<div align="center">

### Turn an entire folder tree into one clean, filtered, auditable text corpus.

**Desktop GUI when you want control. CLI when you want automation. Local processing when your files should stay yours.**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/Desktop-Tkinter-4B8BBE)](#desktop-gui)
[![CLI](https://img.shields.io/badge/Automation-CLI-222222)](#command-line-interface)
[![Local](https://img.shields.io/badge/Processing-Local--first-2E8B57)](#why-file-extractor-pro)
[![Part of Tooltician](https://img.shields.io/badge/Part_of-Tooltician.com-6C47FF?v=2)](https://tooltician.com)

</div>

---

**File Extractor Pro** consolidates the UTF-8 text files you care about from a directory tree into a single readable output file while preserving each file's path, applying precise inclusion/exclusion rules, and optionally producing a machine-readable JSON report.

It is built for the deceptively common job that usually ends in disposable scripts:

> **“Give me the useful contents of this project or folder, but leave out the noise.”**

Use it to package source trees for review, prepare context for AI/LLM workflows, aggregate documentation, collect logs or configuration files, create portable text snapshots, or automate repeatable extraction jobs.

## Why File Extractor Pro?

| What you need | What File Extractor Pro gives you |
| --- | --- |
| **One useful artifact, not a directory maze** | Combines matching files into a single text output with source paths preserved. |
| **Control over what gets included** | Inclusion and exclusion modes, custom extensions, hidden-file control, and file/folder exclusion patterns. |
| **A tool for humans and scripts** | Full desktop GUI plus a headless CLI built on the same extraction service. |
| **Local processing** | Extraction happens on your machine; the application does not need a cloud service to process your files. |
| **Traceability** | Optional JSON reports include per-file size, extension, processing time, and SHA-256 hash. |
| **Large-tree resilience** | Chunked streaming, soft file-size warnings, cancellation support, background processing, and progress/throughput instrumentation. |
| **Low setup friction** | The application itself uses Python's standard library; no third-party runtime framework is required. |

> **The result:** less copy/paste, fewer throwaway scripts, and a reproducible way to turn a messy folder tree into a portable body of text.

## What it produces

Given a tree like:

```text
my-project/
├── README.md
├── src/
│   ├── app.py
│   └── config.py
└── node_modules/
```

File Extractor Pro can produce a single output like:

```text
my-project/README.md:
# My Project
...

my-project/src/app.py:
def main():
    ...

my-project/src/config.py:
...
```

Directories such as `.git`, `.venv`, `node_modules`, `__pycache__`, and other configured exclusions can stay out of the result.

## Built for real workflows

File Extractor Pro is particularly useful when you need to:

- **Package a codebase for review or AI-assisted analysis** without manually opening dozens of files.
- **Aggregate documentation and notes** into a single searchable artifact.
- **Collect selected logs, configuration, CSV, JSON, YAML, Markdown, or source files** from nested directories.
- **Create reproducible project snapshots** with a JSON manifest and SHA-256 hashes.
- **Automate recurring extraction jobs** from shell scripts, scheduled tasks, or other tooling.
- **Explore large directory trees interactively** without blocking the desktop UI during processing.

The default extension set covers common text-oriented project files, and custom extensions can be supplied whenever your workflow needs something else.

## Quick start

### Desktop GUI

Clone the repository and launch it:

```bash
git clone https://github.com/cortega26/File-Extractor-Pro.git
cd File-Extractor-Pro
python file_extractor.py
```

No third-party application runtime dependencies are required. You need **Python 3.9+** and a Python installation with **Tkinter** available.

Then:

1. Select a folder.
2. Choose **Inclusion** or **Exclusion** mode.
3. Pick extensions and optional exclusion patterns.
4. Click **Extract**.
5. Inspect the output and optionally generate a JSON report.

### Command-line interface

For scripts, automation, servers, or terminal-first workflows:

```bash
python -m services.cli /path/to/project --output project-context.txt
```

If you omit `--extensions` in inclusion mode, File Extractor Pro uses its curated common-extension set instead of silently producing an empty result.

## Desktop GUI

The GUI is designed to make repeat extraction work fast rather than merely expose every option.

Highlights include:

- Recent-folder history for quick reuse.
- Inclusion and exclusion modes.
- Common and custom extension selection.
- Hidden-file/folder toggle.
- File and folder exclusion patterns.
- Responsive layout for different window sizes and display scaling.
- Light and dark themes.
- Background extraction with live progress and status output.
- Cancellation of an in-progress extraction.
- JSON report generation.
- Keyboard accelerators:
  - `Alt+E` — Extract
  - `Alt+C` — Cancel
  - `Alt+G` — Generate Report
  - `F5` — Start extraction
  - `Esc` — Cancel extraction

## Command-line interface

### Useful examples

Extract Python, Markdown, and JSON files:

```bash
python -m services.cli ./project \
  --extensions py md json \
  --output project-context.txt
```

Accept comma-separated extensions too:

```bash
python -m services.cli ./project \
  --extensions "py,md,json,yaml" \
  --output project-context.txt
```

Process every file type while still respecting exclusions:

```bash
python -m services.cli ./project \
  --extensions "*" \
  --exclude-folders .git node_modules .venv \
  --output full-context.txt
```

Exclude specific extension types instead:

```bash
python -m services.cli ./project \
  --mode exclusion \
  --extensions log db \
  --output filtered-context.txt
```

Generate an auditable JSON report alongside the output:

```bash
python -m services.cli ./project \
  --output project-context.txt \
  --report extraction-report.json
```

Include hidden files and increase logging detail:

```bash
python -m services.cli ./project \
  --include-hidden \
  --log-level DEBUG
```

### CLI reference

| Flag | Type | Default | Purpose |
| --- | --- | --- | --- |
| `folder` | path | required | Root folder to traverse. |
| `--mode` | choice | `inclusion` | Include matching extensions or exclude them. |
| `--extensions` | list | common set | Extensions to include/exclude; leading dots are optional. |
| `--include-hidden` | flag | off | Traverse hidden files and folders. |
| `--exclude-files` | list | empty | File-name patterns to skip. |
| `--exclude-folders` | list | empty | Folder-name patterns to skip. |
| `--output` | path | `extraction.txt` | Combined text output. |
| `--report` | path | none | Write a JSON extraction report. |
| `--max-file-size-mb` | integer | auto | Soft warning threshold; large files are still streamed. |
| `--poll-interval` | float | `0.1` | Status queue polling interval. |
| `--log-level` | choice | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |

The CLI accepts extension names with or without a leading dot, normalizes case for mode/log-level options, supports comma-separated extension sets, and returns conventional exit codes for successful, failed, or interrupted runs.

## Designed for large and imperfect inputs

File extraction gets awkward when the directory is large, files are huge, queues fill up, encodings are invalid, or users want to stop halfway through. File Extractor Pro treats those as normal operating conditions.

The processing layer:

- Streams file contents in chunks instead of loading an entire file into memory.
- Emits warnings when files exceed a configurable soft size threshold rather than imposing a hard-coded size cap.
- Can reduce chunk size under memory pressure.
- Skips unreadable or non-UTF-8 files cleanly instead of corrupting the combined output.
- Tracks processed/skipped files, throughput, queue depth, dropped status messages, large-file warnings, and completion timestamps.
- Supports cooperative cancellation during traversal and file streaming.
- Preserves terminal state messages under queue pressure.

That instrumentation is also exposed to the CLI logs, making automated jobs easier to observe and diagnose.

## Auditable JSON reports

A report is more than a “files processed” counter. File Extractor Pro records enough metadata to make an extraction inspectable later.

Example shape:

```json
{
  "timestamp": "2026-10-07T12:00:00",
  "total_files": 42,
  "total_size": 183204,
  "extension_summary": {
    ".py": {
      "count": 18,
      "total_size": 92110
    }
  },
  "file_details": {
    "project/src/app.py": {
      "size": 4312,
      "hash": "<sha256>",
      "extension": ".py",
      "processed_time": "<timestamp>"
    }
  }
}
```

This makes reports useful for repeatability, change detection, downstream tooling, and audit trails.

## Configuration

The desktop application persists preferences in `config.ini` and validates them on startup.

<details>
<summary><strong>Configuration reference</strong></summary>

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `output_file` | string | `output.txt` | Default extraction output name. |
| `mode` | string | `inclusion` | `inclusion` or `exclusion`. |
| `include_hidden` | boolean | `false` | Whether hidden files/folders are traversed. |
| `exclude_files` | list | configured defaults | Comma-separated file patterns to exclude. |
| `exclude_folders` | list | configured defaults | Comma-separated folder patterns to exclude. |
| `theme` | string | `light` | `light` or `dark`. |
| `batch_size` | integer | `100` | Batch size used for progress behavior. |
| `max_memory_mb` | integer | `512` | Soft processing safeguard. |
| `recent_folders` | list | `[]` | Recently selected folders for quick access. |

</details>

## Development and quality gates

Install the development tooling:

```bash
pip install -r requirements-dev.txt
```

Run the test suite and coverage checks:

```bash
pytest
python tools/coverage_gate.py
```

The repository configures branch coverage with an **80% overall floor** and includes a helper that enforces **90% per-file coverage** for tracked modules.

Security tooling is also wired into the repository:

```bash
bandit -ll -r .
pip-audit
gitleaks detect --redact
python tools/security_checks.py
```

`gitleaks` is installed separately from its official releases; `bandit` and `pip-audit` are included in the development requirements.

The project also contains dedicated tests for the CLI, extraction engine, service layer, configuration, logging, UI behavior, coverage tooling, type-check tooling, and security checks.

## Project structure

```text
File-Extractor-Pro/
├── file_extractor.py          # Desktop application entry point
├── ui.py                      # Tkinter GUI
├── processor.py               # Traversal, filtering, streaming, metrics
├── config_manager.py          # Persistent validated settings
├── services/
│   ├── cli.py                 # Headless command-line interface
│   └── extractor_service.py   # Background extraction lifecycle
├── ui_support/                # Themes, status, keyboard, layout helpers
├── tools/                     # Coverage, security and type-check gates
└── tests/                     # Automated test suite
```

## Requirements

- **Python 3.9+**
- **Tkinter** for the desktop GUI
- A filesystem containing UTF-8 text files you want to aggregate

The core application uses Python's standard library. Development/test tooling has separate dependencies.

## Current scope

File Extractor Pro is intentionally focused: it **aggregates text-file contents**. It is not a PDF/OCR parser, Office-document converter, archive extractor, or binary-file decoder.

Files that cannot be decoded as UTF-8 are skipped and surfaced through the application's status/error reporting.

## License

This project is declared as **MIT licensed**.

---

<div align="center">

### One folder in. One useful artifact out.

**File Extractor Pro** — local, filterable, repeatable file-content extraction for humans and automation.

[Tooltician.com](https://tooltician.com)

</div>
