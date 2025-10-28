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

## Requirements

- Python 3.9+
- Standard library only (no additional runtime dependencies required)

## License

This project is licensed under the MIT License.
