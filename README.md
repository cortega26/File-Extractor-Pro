# File Extractor Pro

File Extractor Pro is a GUI application to extract and process files based on specified criteria. It allows users to include or exclude files based on extensions, include hidden files, and generate detailed extraction reports.

## Features

- Select a folder to extract files from.
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

## Requirements

- Python 3.9+
- aiofiles

## License

This project is licensed under the MIT License.
