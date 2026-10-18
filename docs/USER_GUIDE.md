# File Extractor Pro - Desktop User Guide

This guide documents the **desktop (Tkinter) interface** of File Extractor Pro. Every statement is verified against the current code (`ui.py`, `services/`, `config_manager.py`, `processor.py`, `constants.py`) and is consistent with `README.md`. For the command-line interface, see the README.

## Starting the desktop app

- Installed package: run `file-extractor-pro-gui` (the GUI console script defined in `pyproject.toml`).
- From a source checkout: run `python file_extractor.py`.
- Requirements: Python 3.9+ and Tkinter.

## Main window at a glance

From top to bottom the window contains:

1. **Folder Path** - text field plus a **Browse** menu button.
2. **Output File** - text field for the combined output file name.
3. **Mode** - **Inclusion** / **Exclusion** radio buttons.
4. **Include Hidden Files** - checkbox.
5. **Select Extensions** - checkboxes for the common extensions.
6. **Custom Extensions (comma separated)** - text field.
7. **Exclude Files** - text field (comma separated).
8. **Exclude Folders** - text field (comma separated).
9. A **progress bar**.
10. An **Actions** group with the **Extract**, **Cancel**, and **Generate Report** buttons.
11. A **status banner** and a scrollable **transcript** that show messages.
12. A **status bar** at the bottom that also surfaces keyboard shortcut hints.

The menu bar has **File > Exit** and **Options > Toggle Theme**.

## Choosing a folder and the Browse menu

The **Browse** menu button opens a menu with:

- **Select Folder...** - opens the system folder chooser.
- A separator, then your **recent folders**, most recent first.

Recent folders are stored in the configuration file, de-duplicated, and the desktop app keeps up to **5** entries (the configuration schema allows at most 10). Long paths are shortened in the menu display, but selecting an entry restores the full path.

When a folder is selected the app:

- fills the **Folder Path** field,
- sets **Output File** to `<folder-name>.txt`,
- records the folder in the recent list,
- saves the configuration.

If a previous session ended with a folder selected, that most recent folder pre-fills the **Folder Path** field on launch.

## Output file

**Output File** holds the destination for the combined text. Its default comes from the saved configuration (`output.txt` unless you have changed it; it becomes `<folder-name>.txt` when you pick a folder).

During a run the output is written to a temporary sibling file and, only after a successful extraction, atomically replaces the destination. A cancelled or failed run therefore leaves any previous output file untouched.

## Mode: Inclusion vs Exclusion

- **Inclusion**: only files whose extension matches the selected extensions are processed.
- **Exclusion**: files whose extension matches the selected extensions are skipped; all other eligible files are processed.

The default is **Inclusion**.

## Selecting extensions

- The **Select Extensions** checkboxes list the common extensions: `.css`, `.csv`, `.db`, `.html`, `.ini`, `.js`, `.json`, `.log`, `.md`, `.py`, `.txt`, `.xml`, `.yaml`, `.yml`. `.txt`, `.md` and `.py` are checked by default.
- **Custom Extensions** accepts a comma-separated list. Tokens are lower-cased, a leading dot is added if missing, `*.ext` is accepted, duplicates are removed while keeping order, and `*` or `*.*` matches every extension (useful in inclusion mode).
- At least one extension must be selected. Starting an extraction without one shows the error: `Please select at least one file extension.`

## Exclusions and hidden files

- **Exclude Files**: comma-separated patterns matched against file names.
- **Exclude Folders**: comma-separated patterns matched against directory names; matching folders are not traversed.
- Patterns use shell-style matching (`fnmatch`) on the file or folder name, not full paths.
- Both fields default to: `.git, .vscode, __pycache__, venv, node_modules, .venv, .pytest_cache`.
- **Include Hidden Files** is off by default; while off, files and folders whose names start with `.` are ignored.
- Symlinked files are always skipped to avoid reading content outside the chosen folder.

## Running an extraction

1. Choose a folder (or type a path).
2. Confirm the output file name.
3. Pick the mode.
4. Select extensions (and optional custom extensions).
5. Adjust exclusions and the hidden-files option.
6. Click **Extract** (or press **Alt+E** / **F5**).

The app validates that a folder, an output name, and at least one extension are present, and reports problems in dialogs. Extraction then runs in a background thread: the **Extract** button is disabled, the progress bar switches between indeterminate and determinate modes, the status bar shows `Processing: X/Y files`, and the transcript receives progress and diagnostic messages.

- If no files match, the status banner warns `No eligible files matched the current filters` and suggests broadening the extension list or enabling hidden files.
- On success the banner reports `Extraction complete - processed N` (plus skipped counts) and a run summary is appended to the transcript.
- Only UTF-8 text is read. Undecodable or binary files are skipped and reported; PDFs, DOCX, images, and archives are not parsed.
- Very large files trigger a soft warning (the threshold derives from the saved `max_memory_mb` value, 512 MB by default) and processing continues via streaming.

There is **no preview button in the GUI**; the read-only preview is a CLI feature.

## Cancelling an extraction

- Click **Cancel**, press **Alt+C**, or press **Esc**. Cancellation only takes effect while a run is in progress.
- Cancellation is cooperative: the worker stops between chunks/files, the staged temporary output is discarded, and the previous output file is preserved.
- After cancelling, the banner shows `Extraction cancelled by user` and you can adjust the filters and start again.
- Closing the window during a run asks for confirmation before exiting.

(The older `user_guide.txt` stated that an extraction cannot be stopped; that is no longer accurate.)

## Generating a report

- Click **Generate Report** or press **Alt+G**.
- If there is no extraction data from the current session, the app shows `No extraction data available. Please run an extraction first.` and writes nothing.
- Otherwise it writes `extraction_report.json` into the **current working directory** (the file name is fixed and is not configurable in the GUI) and shows a dialog with the saved path.

The report contains `timestamp`, `total_files`, `total_size`, `extension_summary`, and a `file_details` entry per processed file with `size`, `hash`, `extension`, and `processed_time`. The `hash` is the SHA-256 of the UTF-8 text streamed into the output.

## Themes

- The app ships **light** and **dark** themes and starts in the theme saved in the configuration (light by default).
- Toggle with **Options > Toggle Theme**. The choice is written back to the configuration file.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Alt+E` or `F5` | Start extraction |
| `Alt+C` or `Esc` | Cancel extraction |
| `Alt+G` | Generate report |

Hovering or focusing a button also shows its shortcut hint in the status bar.

## Saved settings

The app stores its settings in `config.ini` in the current working directory: output file, mode, hidden-files flag, exclude files/folders, theme, and the recent-folder list. Settings load on launch and are written when you change them.

## Troubleshooting

- **`Please select a folder.` / `Please specify an output file name.` / `Please select at least one file extension.`** - the matching field is empty; fill it in before extracting.
- **Nothing is extracted** - broaden the extension selection, enable hidden files, or check the exclusion patterns.
- **A file is skipped** - it may be undecodable in UTF-8, a symlink, or excluded by a pattern; the transcript reports the reason.
- **A large-file warning appears** - the file exceeds the soft threshold; processing still continues.
- **The output file was not updated** - the run was cancelled or failed; the previous output is preserved by design.
