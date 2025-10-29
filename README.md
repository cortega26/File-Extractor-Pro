# File Extractor Pro

File Extractor Pro is a GUI application to extract and process files based on specified criteria. It allows users to include or exclude files based on extensions, include hidden files, and generate detailed extraction reports.

## Features

- Select a folder to extract files from with a dropdown history of recent paths.
- Choose between inclusion or exclusion mode for file extensions.
- Include or exclude hidden files and folders.
- Specify custom file extensions to include or exclude.
- Exclude specific files and folders by name.
- Accurate progress tracking and status updates.
- Generate detailed extraction reports in JSON format.
- Asynchronous file processing for improved performance.
- Error handling and logging for robustness.
- Streams large files without a hard-coded size cap while emitting warnings
  when configurable soft limits are exceeded.

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/cortega26/File-Extractor-Pro.git
    cd file-extractor-pro
    ```

2. Create a virtual environment and activate it:

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. Install the required dependencies:

    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Run the application:

    ```sh
    python file_extractor.py
    ```

2. Use the GUI to select a folder, set the criteria, and start the extraction process.

3. View progress and logs in the application window.

4. Generate and view extraction reports.

### Command-line usage

Run headless extractions via the CLI module:

```sh
python -m services.cli /path/to/folder
```

- `--mode` defaults to `inclusion`. When omitted, the CLI processes files with
  a curated set of common extensions (for example `.txt`, `.md`, `.py`).
- Extensions may be supplied with or without a leading dot. `--extensions txt md`
  is normalised to `(.txt, .md)` automatically.
- Use `--extensions "*"` to process all file types in inclusion mode while still
  respecting exclude patterns.
- Provide comma-separated lists for long extension sets: `--extensions "txt,md,pdf"`.
- In exclusion mode, omit `--extensions` to process all files or provide the
  extensions that should be skipped.
- Append `--include-hidden` to traverse hidden files and folders.
- Provide `--max-file-size-mb` to emit warnings for files exceeding the
  specified soft limit while still streaming their contents. When omitted, the
  processor derives a soft cap from available system memory to avoid
  `MemoryError` regressions.
- Adjust `--poll-interval` (seconds) and `--log-level` (`DEBUG`–`CRITICAL`) to
  tune queue responsiveness and console verbosity.
- Use `--report` to generate a JSON snapshot of the latest extraction summary on
  disk.
- Each run logs throughput metrics (files processed, elapsed time, files per
  second, queue saturation, dropped status messages, and skipped files) at the
  end of the execution to aid monitoring.
- Programmatic consumers that instantiate `CLIOptions` directly inherit
  the same default extension set when running in inclusion mode, preventing
  empty extraction results.

| Flag | Type | Default | Description |
| ---- | ---- | ------- | ----------- |
| `folder` | positional path | required | Folder to extract files from. |
| `--mode` | choice | `inclusion` | Choose between inclusion and exclusion filtering. |
| `--extensions` | list | varies | Extensions to include/exclude; defaults to common types in inclusion mode. |
| `--include-hidden` | boolean | `false` | Traverse hidden files and folders. |
| `--exclude-files` | list | `[]` | File patterns to skip during extraction. |
| `--exclude-folders` | list | `[]` | Folder patterns to skip. |
| `--output` | path | `extraction.txt` | Destination text file for extracted content. |
| `--report` | path | none | Optional JSON report output location. |
| `--max-file-size-mb` | int | auto | Soft warning threshold for large files; defaults to available memory. |
| `--poll-interval` | float | `0.1` | Queue polling interval while monitoring extraction progress. |
| `--log-level` | choice | `INFO` | Console logging verbosity. |

## Configuration

The application persists user preferences to `config.ini`. Values are validated at
startup to prevent invalid modes or resource limits from causing runtime errors.

| Name             | Type    | Default      | Required | Description |
| ---------------- | ------- | ------------ | -------- | ----------- |
| `output_file`    | string  | `output.txt` | No       | Default filename used when generating extraction output. |
| `mode`           | string  | `inclusion`  | No       | Extraction mode. Must be either `inclusion` or `exclusion`. |
| `include_hidden` | boolean | `false`      | No       | Controls whether hidden files and folders are processed. Accepts `true/false`, `yes/no`, or `1/0`. |
| `exclude_files`  | list    | see defaults | No       | Comma-separated list of file patterns to exclude from extraction. |
| `exclude_folders`| list    | see defaults | No       | Comma-separated list of folder patterns to exclude from extraction. |
| `theme`          | string  | `light`      | No       | UI theme preference. Must be `light` or `dark`. |
| `batch_size`     | integer | `100`        | No       | Number of files processed before UI progress updates. Must be greater than zero. |
| `max_memory_mb`  | integer | `512`        | No       | Soft memory cap used for processing safeguards. Must be greater than zero. |
| `recent_folders` | list    | `[]`         | No       | JSON array tracking the most recently selected folders for quick access in the Browse menu. |

## Testing

Install development dependencies to enable coverage and security tooling:

```sh
pip install -r requirements-dev.txt
```

Run the full suite with coverage thresholds enforced:

```sh
pytest
```

The configuration enables branch coverage and fails the run when overall coverage
drops below 80%. Aim for ≥90% coverage on changed modules to satisfy internal
quality targets.

## Security Scans

Run the required security tooling before submitting changes:

```sh
bandit -ll -r .
pip-audit
gitleaks detect --redact
python tools/security_checks.py  # Runs all scanners sequentially
```

All three tools install via `requirements-dev.txt`. Capture and address any
medium- or high-severity findings before merging.

## Requirements

- Python 3.9+
- Standard library only (no additional runtime dependencies required)

## License

This project is licensed under the MIT License.
