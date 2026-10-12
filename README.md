# File Extractor Pro

<div align="center">

### One folder. The files that matter. One readable output.

**Preview and package source code, documentation, logs, and configuration files — locally, with a desktop app or a scriptable CLI.**

[![Tests](https://github.com/cortega26/File-Extractor-Pro/actions/workflows/tests.yml/badge.svg)](https://github.com/cortega26/File-Extractor-Pro/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI + CLI](https://img.shields.io/badge/Interfaces-GUI%20%2B%20CLI-344054)](#two-ways-to-work)
[![Local processing](https://img.shields.io/badge/Processing-Local-147D64)](#know-before-you-export)
[![MIT license](https://img.shields.io/badge/License-MIT-2962A3)](LICENSE)

[Quick start](#quick-start) · [See it in action](#see-it-in-action) · [Examples](#cli-cookbook) · [Limitations](#know-before-you-export)

</div>

---

Opening 40 files just to share the useful parts of a project shouldn't take 40 copy-and-paste operations.

**File Extractor Pro** walks a directory tree, selects the text files you care about, and combines them into one clearly labeled document. Inspect the selection first with a **read-only preview**, work interactively in **Tkinter**, or run the same extraction engine in a **CLI** for repeatable tasks.

No account, API key, cloud upload, or third-party runtime package is required.

## Quick start

**Requirements:** Python 3.9+; Tkinter is additionally required for the desktop interface.

```bash
git clone https://github.com/cortega26/File-Extractor-Pro.git
cd File-Extractor-Pro
```

**1. Preview a folder without writing an output file:**

```bash
python -m services.cli ./my-project \
  --extensions py md json yaml \
  --exclude-folders node_modules .venv build dist \
  --dry-run
```

**2. Extract those files and generate a JSON report:** remove `--dry-run` and give the output an explicit destination.

```bash
python -m services.cli ./my-project \
  --extensions py md json yaml \
  --exclude-folders node_modules .venv build dist \
  --output ./project-context.txt \
  --report ./extraction-report.json
```

**Prefer a desktop window?**

```bash
python file_extractor.py
```

Choose a folder, tune inclusion/exclusion rules, and select **Extract**. The interface shows progress, supports cancellation, and can generate a report.

> **Tip:** Run commands from the cloned File-Extractor-Pro directory, replacing `./my-project` with a real folder path. The example output paths are illustrative.

## See it in action

Suppose your source tree looks like this:

```text
my-project/
├── README.md
├── src/
│   ├── app.py
│   └── settings.py
├── node_modules/
└── .venv/
```

Preview the selection:

```bash
python -m services.cli ./my-project \
  --extensions md py \
  --exclude-folders node_modules .venv \
  --dry-run
```

The output is a readable inventory of **selected file paths and source byte sizes**:

```text
File Extractor Pro — read-only preview
Source: /absolute/path/to/my-project
Output: extraction.txt
Selected: 3 files, ... source bytes

  README.md  (... bytes)
  src/app.py  (... bytes)
  src/settings.py  (... bytes)
```

*Illustrative display; paths and sizes depend on your files.*

Run the same command without `--dry-run` and with `--output project-context.txt` to generate a combined UTF-8 text file:

```text
my-project/README.md:
# My project
...

my-project/src/app.py:
def main():
    ...

my-project/src/settings.py:
...
```

Each section keeps its source path so readers can identify where its content came from. The original files are read, not edited.

## What you get

| Capability | Why it matters |
| --- | --- |
| **Preview before extraction** | See selected paths, source sizes, totals, and an existing-output warning without writing the extraction or report files. |
| **Fine-grained selection** | Include or exclude extensions, files, folders, and hidden entries. |
| **Readable combined output** | Concatenate UTF-8 text with clear source-path separators. |
| **Optional JSON report** | Inspect per-file sizes, extensions, processing timestamps, and SHA-256 hashes of processed text. |
| **Safe completion behavior** | Output is staged in a temporary sibling file and atomically replaced after successful extraction. |
| **Predictable ordering** | Deterministic directory/file traversal; eligible top-level README/specification files come first. |
| **Works at a desk or in automation** | Tkinter GUI and headless CLI share the extraction service. |
| **Built for large folder trees** | Chunked reading, soft size warnings, cooperative cancellation, and progress/throughput metrics. |

### Good fits

- **Code reviews and AI-assisted development:** hand a reviewer a controlled text snapshot rather than an entire directory.
- **Documentation handoffs:** consolidate Markdown, text notes, and configuration samples.
- **Incident investigation:** gather relevant text logs or config files from nested folders.
- **Reproducible automation:** use the CLI and JSON report in scripts or scheduled workflows.

**It packages context; it does not interpret, summarize, or analyze it with AI.**

## Two ways to work

### Desktop app

Launch with `python file_extractor.py`. The GUI includes:

- Folder picker and recently used folders
- Inclusion/exclusion modes and custom extensions
- Hidden-file controls and filename/folder patterns
- Light/dark themes and a resizable layout
- Background extraction, live progress, cancellation, and JSON reports

**Keyboard shortcuts**

| Shortcut | Action |
| --- | --- |
| `Alt+E` or `F5` | Start extraction |
| `Alt+C` or `Esc` | Cancel |
| `Alt+G` | Generate report |

The **read-only preview is currently a CLI feature**, not a GUI button.

### Command-line interface

Run `python -m services.cli --help` for the current CLI help.

<details>
<summary><strong>CLI options</strong></summary>

| Argument | Default | Purpose |
| --- | --- | --- |
| `folder` | Required | Root directory |
| `--mode inclusion\|exclusion` | `inclusion` | Include or exclude listed extensions |
| `--extensions py md` | Common extension set | Extensions to include or exclude; comma-separated values also work |
| `--exclude-files PATTERN ...` | None | Skip matching filenames |
| `--exclude-folders PATTERN ...` | None | Skip matching folder names |
| `--include-hidden` | Off | Consider hidden files and directories |
| `--dry-run` | Off | Preview selection without writing output/report |
| `--preview-format text\|json` | `text` | Preview formatting (`--dry-run` only) |
| `--output PATH` | `extraction.txt` | Combined text output |
| `--report PATH` | None | Optional JSON report after extraction |
| `--max-file-size-mb N` | Automatic | Soft warning threshold; not a hard rejection limit |
| `--poll-interval SECONDS` | `0.1` | Status polling interval |
| `--log-level LEVEL` | `INFO` | Logging verbosity |

</details>

## CLI cookbook

**Get a JSON preview for another tool to consume**

```bash
python -m services.cli ./my-project \
  --extensions py md json \
  --dry-run --preview-format json > selection.json
```

This writes `selection.json` through your **shell's redirection**, not through the extractor. The extractor does not create its configured output/report in dry-run mode.

**Package only Python and Markdown**

```bash
python -m services.cli ./my-project \
  --extensions py md \
  --output ./code-review.txt
```

**Use explicit directory and file exclusions**

```bash
python -m services.cli ./my-project \
  --extensions py md yaml \
  --exclude-folders node_modules .venv dist build \
  --exclude-files "*.generated.py" "*.min.js" \
  --output ./filtered-context.txt
```

**Collect text while excluding certain extension types**

```bash
python -m services.cli ./my-project \
  --mode exclusion --extensions log db \
  --exclude-folders node_modules .venv \
  --output ./filtered-files.txt
```

**Inspect every candidate filename, including hidden ones**

```bash
python -m services.cli ./my-project \
  --extensions "*" --include-hidden \
  --exclude-folders .git node_modules .venv \
  --dry-run
```

This last command is intentionally broad. It may select secrets or binary files; inspect the result carefully before extraction.

## Know before you export

A clear understanding of the current boundaries is part of a trustworthy extraction workflow.

| Behavior | Important detail |
| --- | --- |
| **Text only** | The extractor reads UTF-8 text. Undecodable or binary files are skipped with diagnostics; it does not parse PDFs, DOCX, images, archives, or OCR. |
| **Preview ≠ content validation** | Dry-run checks selection and file sizes, not encoding, readability, security, or LLM token count. |
| **No automatic `.gitignore` parsing** | Supply explicit `--exclude-files` and `--exclude-folders` patterns. CLI exclusion lists are empty by default; GUI configuration has its own defaults. |
| **No secret scanning** | Be careful with credentials, personal information, and hidden config files; review before sharing output. |
| **Symlinks** | Symlinked files are skipped to avoid unintentionally reading content outside the selected tree. |
| **Output replacement** | Failed or cancelled runs preserve an existing destination. **Successful runs replace it**, rather than creating a backup. |
| **Source files** | Original files are not modified by extraction. |

Patterns currently match **file/folder names**, not full Git-style path rules. For a large repository, use explicit exclusions for dependency directories, generated artifacts, and other irrelevant content.

## JSON reports

Request a report using `--report extraction-report.json`. The structure resembles:

```json
{
  "timestamp": "2026-10-12T10:30:00",
  "total_files": 1,
  "total_size": 19,
  "extension_summary": {
    ".py": { "count": 1, "total_size": 19 }
  },
  "file_details": {
    "my-project/src/app.py": {
      "size": 19,
      "hash": "<sha256>",
      "extension": ".py",
      "processed_time": "<timestamp>"
    }
  }
}
```

*Illustrative values.* The report records processed files and SHA-256 hashes of the text streamed into the output (not necessarily raw on-disk byte hashes if newline decoding changes the bytes). This is useful for auditability, but is not a cryptographic attestation of a complete repository.

## Development

Runtime dependencies are limited to the Python standard library (with Tkinter available for the GUI). To work on the code:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/coverage_gate.py
```

[GitHub Actions](https://github.com/cortega26/File-Extractor-Pro/actions/workflows/tests.yml) runs the pytest suite on pull requests and `main`, with an **80% overall coverage requirement**. Separate development scripts under `tools/` provide additional coverage, security, and type-check checks; these are **not all part of the current CI workflow**.

<details>
<summary><strong>Repository map</strong></summary>

```text
file_extractor.py          Desktop entry point
ui.py                      Tkinter interface
processor.py               Discovery, filtering, streaming, metrics
config_manager.py          Validated desktop preferences
services/
  cli.py                   Headless commands
  preview.py               Read-only selection planning
  extractor_service.py     Background lifecycle and reports
ui_support/                Theme, layout, keyboard, status helpers
tests/                     Automated regression tests
tools/                     Local validation utilities
.github/workflows/         CI test workflow
```

</details>

## Contributing

Found an issue, a file-selection edge case, or an opportunity to make the workflow simpler? [Open an issue](https://github.com/cortega26/File-Extractor-Pro/issues). Small, test-backed changes are especially welcome.

## License

Distributed under the [MIT License](LICENSE).

---

<div align="center">

**Turn scattered files into a useful, inspectable handoff.**

Part of [Tooltician](https://tooltician.com).

</div>
