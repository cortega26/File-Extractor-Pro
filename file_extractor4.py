"""
File Extractor Pro - Advanced File Processing Utility

A professional-grade utility for extracting and processing files with features including:
- Multi-threaded file processing for a responsive UI
- Advanced error handling and robust logging
- System resource monitoring
- Modern, configurable UI with themes
- Comprehensive progress tracking and detailed reporting
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
from typing import List, Dict, Any, Set, Optional, Tuple
import logging
import threading
import queue
import asyncio
import aiofiles
import json
import hashlib
from datetime import datetime, timedelta
import fnmatch
import configparser
from logging.handlers import RotatingFileHandler
import time
import platform
import psutil
import shutil
import subprocess


# Version information
__version__ = "2.1.2"
__author__ = "Your Company"
__license__ = "MIT"

# Application Constants
APP_NAME = "File Extractor Pro"
APP_DESCRIPTION = "Professional File Processing Utility"
SUPPORT_URL = "https://github.com/cortega26/File-Extractor-Pro"
DOCS_URL = "https://your-company.com/docs"

# System Constants
MAX_RECENT_FOLDERS = 5
AUTO_SAVE_INTERVAL = 300  # 5 minutes in seconds
MEMORY_WARNING_THRESHOLD = 85  # Percentage
DISK_WARNING_THRESHOLD = 90  # Percentage
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 8192  # Optimal chunk size for file reading
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds

# File Processing Constants
COMMON_EXTENSIONS: List[str] = [
    ".css", ".csv", ".html", ".ini", ".js", ".json",
    ".log", ".md", ".py", ".txt", ".xml", ".yaml", ".yml"
]

DEFAULT_EXCLUDE_FILES: List[str] = [
    "*.pyc", "*.pyo", "*.pyd", "*.so",
    "*.dll", "*.dylib",
    "*.log", "*.tmp",
    "*.swp", "*.swo",
    ".DS_Store", "Thumbs.db",
    ".env", "*.bak",
    "*.cache", "*.egg-info",
    ".coverage", "coverage.xml",
    ".pytest_cache"
]

DEFAULT_EXCLUDE_FOLDERS: List[str] = [
    ".git", ".github",
    ".vscode", ".idea",
    "__pycache__",
    "venv", ".venv",
    "node_modules",
    "dist", "build",
    "backup", "/backup",
    "env", "virtualenv",
    ".pytest_cache",
    ".coverage_cache",
    "*.egg-info"
]

SPECIFICATION_FILES: List[str] = ["README.md", "SPECIFICATIONS.md"]

# Theme Configuration
THEME_CONFIG = {
    'light': {
        'bg': '#f0f0f0',
        'fg': '#000000',
        'active_bg': '#e0e0e0',
        'active_fg': '#000000',
        'text_bg': '#ffffff',
        'text_fg': '#000000',
        'button_bg': '#e0e0e0',
        'button_fg': '#000000',
        'highlight_bg': '#0078d7',
        'highlight_fg': '#ffffff'
    },
    'dark': {
        'bg': '#2d2d2d',
        'fg': '#ffffff',
        'active_bg': '#4d4d4d',
        'active_fg': '#ffffff',
        'text_bg': '#1e1e1e',
        'text_fg': '#ffffff',
        'button_bg': '#4d4d4d',
        'button_fg': '#ffffff',
        'highlight_bg': '#0078d7',
        'highlight_fg': '#ffffff'
    }
}

UI_CONSTANTS = {
    'PADDING': {
        'frame': 10,
        'widget': 5,
        'section': 15
    },
    'DIMENSIONS': {
        'width': 1024,
        'height': 700,
        'min_width': 1000,
        'min_height': 600,
        'max_screen_ratio': 0.8
    },
    'COLORS': {
        'light': {
            'bg': '#ffffff',
            'fg': '#333333',
            'accent': '#007acc',
            'button': '#f0f0f0',
            'button_hover': '#e0e0e0',
            'frame_bg': '#f8f8f8',
            'input_bg': '#ffffff',
            'border': '#cccccc',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545'
        },
        'dark': {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#0098ff',
            'button': '#333333',
            'button_hover': '#404040',
            'frame_bg': '#252526',
            'input_bg': '#2d2d2d',
            'border': '#404040',
            'success': '#28a745',
            'warning': '#ffc107',
            'error': '#dc3545'
        }
    },
    'FONTS': {
        'default': ('Segoe UI', 9),
        'header': ('Segoe UI', 10, 'bold'),
        'title': ('Segoe UI', 12, 'bold')
    }
}

# Setup enhanced logging
def setup_logging() -> None:
    """Configure application logging with rotation and formatting."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "file_extractor.log")

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s"
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

# Utility Functions
def get_formatted_size(size_in_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_in_bytes is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    return str(timedelta(seconds=int(seconds)))

def check_system_resources() -> Tuple[float, float]:
    """Check system memory usage and disk space."""
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return memory.percent, disk.percent
    except Exception as e:
        logging.error(f"Error checking system resources: {str(e)}")
        return 0.0, 0.0

def is_valid_file_name(filename: str) -> bool:
    """
    Validate file name for illegal characters and system restrictions.

    Args:
        filename (str): The filename to validate

    Returns:
        bool: True if filename is valid, False otherwise
    """
    if not filename:
        return False

    # Check for illegal characters
    illegal_chars = '<>:"/\\|?*'
    if any(char in filename for char in illegal_chars):
        return False

    # Check for reserved names on Windows
    if platform.system() == 'Windows':
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4',
            'LPT1', 'LPT2', 'LPT3', 'LPT4'
        }
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            return False

    return True

def create_unique_filename(base_path: str, filename: str) -> str:
    """
    Create a unique filename by appending a number if the file already exists.
    This version is more robust against race conditions.

    Args:
        base_path (str): The directory path
        filename (str): The desired filename

    Returns:
        str: A unique filename
    """
    if not os.path.exists(os.path.join(base_path, filename)):
        return filename

    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_filename = f"{name}_{counter}{ext}"
        try:
            # Attempt to create the file exclusively
            with open(os.path.join(base_path, new_filename), 'x') as f:
                pass
            # If successful, we have our unique name
            os.remove(os.path.join(base_path, new_filename)) # Clean up the empty file
            return new_filename
        except FileExistsError:
            # If the file exists, increment the counter and try again
            counter += 1
        except Exception as e:
            # Handle other potential errors, like permissions
            logging.error(f"Error creating unique filename: {e}")
            # Fallback to the original logic as a last resort
            if not os.path.exists(os.path.join(base_path, new_filename)):
                 return new_filename
            counter += 1


def get_system_info() -> Dict[str, str]:
    """
    Get detailed system information.

    Returns:
        Dict[str, str]: Dictionary containing system information
    """
    try:
        login_user = os.getlogin()
    except Exception:
        login_user = "N/A"

    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'processor': platform.processor(),
        'memory': f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
        'cpu_count': str(psutil.cpu_count()),
        'username': login_user,
        'hostname': platform.node()
    }


def calculate_file_hash(file_path: str, hash_type: str = 'md5') -> Optional[str]:
    """
    Calculate file hash using specified algorithm.

    Args:
        file_path (str): Path to the file
        hash_type (str): Hash algorithm to use ('md5', 'sha1', 'sha256')

    Returns:
        Optional[str]: Hash string or None if error occurs
    """
    try:
        hash_func = getattr(hashlib, hash_type)()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logging.error(f"Error calculating file hash for {file_path}: {str(e)}")
        return None

# Initialize logging
setup_logging()
logging.info(f"Starting {APP_NAME} version {__version__}")

class Config:
    """Enhanced configuration manager with improved error handling and validation."""

    def __init__(self, config_file: str = 'config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.last_save = time.time()
        self.last_auto_save = time.time()
        self.load()

    def load(self) -> None:
        """Load configuration with enhanced error handling."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
                logging.info(f"Configuration loaded from: {self.config_file}")
            else:
                self.set_defaults()
                logging.info(f"Created new configuration file: {self.config_file}")
        except Exception as e:
            logging.error(f"Error loading configuration: {str(e)}")
            self.set_defaults()

    def save(self, force: bool = False) -> None:
        """
        Save configuration with improved error handling and auto-save support.

        Args:
            force (bool): Force save regardless of auto-save interval
        """
        current_time = time.time()

        # Check if we should auto-save
        if not force and (current_time - self.last_auto_save) < AUTO_SAVE_INTERVAL:
            return

        try:
            # Create backup of existing config
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.backup"
                shutil.copy2(self.config_file, backup_file)

            # Save new config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)

            self.last_save = current_time
            self.last_auto_save = current_time
            logging.debug("Configuration saved successfully")

            # Remove backup if save was successful
            if 'backup_file' in locals() and os.path.exists(backup_file):
                os.remove(backup_file)

        except Exception as e:
            logging.error(f"Error saving configuration: {str(e)}")
            # Restore from backup if available
            if 'backup_file' in locals() and os.path.exists(backup_file):
                try:
                    shutil.copy2(backup_file, self.config_file)
                    logging.info("Configuration restored from backup")
                except Exception as backup_e:
                    logging.error(f"Error restoring configuration backup: {str(backup_e)}")

    def set_defaults(self) -> None:
        """Set default configuration values with enhanced options."""
        self.config['DEFAULT'] = {
            'output_file': 'output.txt',
            'mode': 'inclusion',
            'include_hidden': 'false',
            'exclude_files': ', '.join(DEFAULT_EXCLUDE_FILES),
            'exclude_folders': ', '.join(DEFAULT_EXCLUDE_FOLDERS),
            'theme': 'system',
            'batch_size': '100',
            'max_memory_mb': '512',
            'auto_save': 'true',
            'recent_folders': '',
            'last_directory': '',
            'confirm_overwrite': 'true',
            'show_tooltips': 'true',
            'max_file_size': str(MAX_FILE_SIZE),
            'chunk_size': str(CHUNK_SIZE),
            'retry_attempts': str(MAX_RETRY_ATTEMPTS),
            'retry_delay': str(RETRY_DELAY),
            'debug_mode': 'false',
            'use_relative_paths': 'true',
            'preserve_timestamps': 'true',
            'verify_hashes': 'true',
            'compress_output': 'false',
            'backup_config': 'true',
            'logging_level': 'INFO'
        }
        self.save(force=True)

    def get(self, key: str, fallback: Any = None) -> Any:
        """
        Get configuration value with enhanced type checking and validation.

        Args:
            key (str): Configuration key
            fallback (Any): Fallback value if key doesn't exist

        Returns:
            Any: Configuration value or fallback
        """
        try:
            value = self.config.get('DEFAULT', key, fallback=fallback)

            # Type conversion based on fallback type
            if fallback is not None:
                if isinstance(fallback, bool):
                    if isinstance(value, bool):  # If already boolean
                        return value
                    return value.lower() == 'true'
                elif isinstance(fallback, int):
                    return int(value)
                elif isinstance(fallback, float):
                    return float(value)

            return value
        except Exception as e:
            logging.warning(f"Error getting config value for {key}: {str(e)}")
            return fallback

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value with validation and type conversion.

        Args:
            key (str): Configuration key
            value (Any): Value to set
        """
        try:
            # Convert value to string based on type
            if isinstance(value, bool):
                str_value = str(value).lower()
            else:
                str_value = str(value)

            self.config.set('DEFAULT', key, str_value)

            # Auto-save if enabled
            if self.get('auto_save', True):
                self.save()

        except Exception as e:
            logging.error(f"Error setting config value {key}: {str(e)}")

class FileProcessor:
    """Enhanced file processor with improved error handling and performance."""

    def __init__(self, output_queue: queue.Queue, config: Config):
        self.output_queue = output_queue
        self.config = config
        self.extraction_summary: Dict[str, Any] = {}
        self.processed_files: Set[str] = set()
        self._cache: Dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.should_stop = False
        self._setup_cache()

    def _setup_cache(self) -> None:
        """Initialize cache with configurable size limit."""
        self._cache = {
            'file_stats': {},
            'content_hashes': {},
            'failed_files': set(),
            'skipped_files': set()
        }

    def clear_cache(self) -> None:
        """Clear processor cache."""
        self._cache.clear()
        self._setup_cache()

    async def process_specifications(self, directory_path: str, output_file: Any) -> None:
        """
        Process specification files first with enhanced error handling.

        Args:
            directory_path (str): Base directory path
            output_file (Any): Output file object
        """
        for spec_file in SPECIFICATION_FILES:
            try:
                file_path = os.path.join(directory_path, spec_file)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    logging.info(f"Processing specification file: {spec_file}")
                    await self.process_file(file_path, output_file)
                    self.processed_files.add(file_path)
            except Exception as e:
                logging.error(f"Error processing specification file {spec_file}: {str(e)}")
                self.output_queue.put(("error", f"Error processing {spec_file}: {str(e)}"))

    async def process_file(self, file_path: str, output_file: Any) -> None:
        """
        Process individual file with improved error handling and memory management.

        Args:
            file_path (str): Path to the file to process
            output_file (Any): Output file object
        """
        if self.should_stop:
            return

        try:
            # Validate file
            if not self._validate_file(file_path):
                return

            # Get file stats with caching
            if file_path in self._cache['file_stats']:
                file_size = self._cache['file_stats'][file_path]['size']
            else:
                file_size = os.path.getsize(file_path)
                self._cache['file_stats'][file_path] = {'size': file_size}

            # Check file size limit
            max_size = self.config.get('max_file_size', MAX_FILE_SIZE)
            if file_size > max_size:
                raise MemoryError(f"File too large to process: {get_formatted_size(file_size)}")

            normalized_path = os.path.normpath(file_path).replace(os.path.sep, "/")

            # Process file in chunks with enhanced memory management
            content = []
            chunk_size = self.config.get('chunk_size', CHUNK_SIZE)

            async with aiofiles.open(file_path, "r", encoding="utf-8", errors='ignore') as f:
                while chunk := await f.read(chunk_size):
                    if self.should_stop:
                        return
                    content.append(chunk)

            file_content = "".join(content)

            # Write to output with relative paths if configured
            if self.config.get('use_relative_paths', True):
                try:
                    relative_path = os.path.relpath(normalized_path)
                    normalized_path = relative_path
                except ValueError:
                    pass  # Keep absolute path if relative path cannot be computed

            await output_file.write(f"--- File: {normalized_path} ---\n")
            await output_file.write(f"{file_content}\n\n")


            # Calculate file hash if enabled
            file_hash = None
            if self.config.get('verify_hashes', True):
                file_hash = calculate_file_hash(file_path)
                self._cache['content_hashes'][file_path] = file_hash

            # Update extraction summary
            file_ext = os.path.splitext(file_path)[1]
            self._update_extraction_summary(file_ext, file_path, file_size, file_hash)

            logging.debug(f"Successfully processed file: {file_path}")

        except (UnicodeDecodeError, UnicodeError) as e:
            self._handle_file_error(file_path, f"Cannot decode file: {str(e)}")
        except Exception as e:
            self._handle_file_error(file_path, f"Error processing file: {str(e)}")

    def _validate_file(self, file_path: str) -> bool:
        """
        Validate file before processing.

        Args:
            file_path (str): Path to the file to validate

        Returns:
            bool: True if file is valid, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if not os.path.isfile(file_path):
                raise ValueError(f"Not a file: {file_path}")

            if not os.access(file_path, os.R_OK):
                raise PermissionError(f"Permission denied: {file_path}")

            return True

        except Exception as e:
            self._handle_file_error(file_path, str(e))
            return False

    def _handle_file_error(self, file_path: str, error_msg: str) -> None:
        """
        Handle file processing errors with retry logic.

        Args:
            file_path (str): Path to the file
            error_msg (str): Error message
        """
        logging.error(f"Error processing {file_path}: {error_msg}")
        self.output_queue.put(("error", f"Error processing {file_path}: {error_msg}"))
        self._cache['failed_files'].add(file_path)

    def _update_extraction_summary(self, file_ext: str, file_path: str,
                                 file_size: int, file_hash: Optional[str]) -> None:
        """
        Update extraction summary with thread safety and enhanced statistics.

        Args:
            file_ext (str): File extension
            file_path (str): Path to the file
            file_size (int): Size of the file
            file_hash (Optional[str]): File hash if calculated
        """
        try:
            # Update extension statistics
            if file_ext not in self.extraction_summary:
                self.extraction_summary[file_ext] = {
                    "count": 0,
                    "total_size": 0,
                    "min_size": float('inf'),
                    "max_size": 0
                }

            ext_summary = self.extraction_summary[file_ext]
            ext_summary["count"] += 1
            ext_summary["total_size"] += file_size
            ext_summary["min_size"] = min(ext_summary["min_size"], file_size)
            ext_summary["max_size"] = max(ext_summary["max_size"], file_size)

            # Update file details
            self.extraction_summary[file_path] = {
                "size": file_size,
                "hash": file_hash,
                "extension": file_ext,
                "processed_time": datetime.now().isoformat(),
                "relative_path": os.path.relpath(file_path) if self.config.get('use_relative_paths', True) else file_path
            }

        except Exception as e:
            logging.error(f"Error updating extraction summary: {str(e)}")

    # Update the extract_files method in FileProcessor class
    async def extract_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str],
        output_file_name: str,
        ) -> None:
        """Extract files with improved error handling and progress reporting."""
        self.start_time = time.time()
        self.should_stop = False
        total_files = 0
        processed_files = 0
        output_file = None

        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_file_name)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Process files directly to final output instead of using a temp file
            async with aiofiles.open(output_file_name, "w", encoding="utf-8") as output_file:
                # Write header with metadata
                await self._write_output_header(output_file, folder_path)

                # Process specification files first
                await self.process_specifications(folder_path, output_file)

                # Count total files for the progress bar
                self.output_queue.put(("status", "Counting files to process..."))
                total_files = await self._count_total_files(
                    folder_path, mode, include_hidden,
                    extensions, exclude_files, exclude_folders
                )
                self.output_queue.put(("progress_init", total_files))


                # Process remaining files
                processed_files = await self._process_files(
                    folder_path, mode, include_hidden,
                    extensions, exclude_files, exclude_folders,
                    output_file, total_files
                )

                # Write footer with summary
                await self._write_output_footer(output_file, processed_files, total_files)

                # Signal successful completion
                completion_message = (f"Extraction complete. Processed {processed_files}/{total_files} files. "
                                      f"Results written to {output_file_name}.")
                self.output_queue.put(("info", completion_message))
                self.output_queue.put(("completion", True))


        except Exception as e:
            error_msg = f"Error during extraction: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.output_queue.put(("error", error_msg))
            self.output_queue.put(("completion", False))


    async def _write_output_header(self, output_file: Any, folder_path: str) -> None:
        """Write metadata header to output file."""
        header = (
            f"File Extraction Report\n"
            f"Generated: {datetime.now().isoformat()}\n"
            f"Source Directory: {folder_path}\n"
            f"System Info: {platform.platform()}\n"
            f"Python Version: {platform.python_version()}\n"
            f"{'='*80}\n\n"
        )
        await output_file.write(header)

    async def _write_output_footer(self, output_file: Any, processed_files: int, total_files: int) -> None:
        """Write summary footer to output file."""
        if self.start_time is None:
            return
        duration = time.time() - self.start_time
        footer = (
            f"\n{'='*80}\n"
            f"Extraction Summary:\n"
            f"Total Files Encountered: {total_files}\n"
            f"Processed Files: {processed_files}\n"
            f"Failed Files: {len(self._cache['failed_files'])}\n"
            f"Skipped Files (e.g., due to size): {len(self._cache['skipped_files'])}\n"
            f"Duration: {format_duration(duration)}\n"
            f"End Time: {datetime.now().isoformat()}\n"
        )
        await output_file.write(footer)


    async def _count_total_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str]
    ) -> int:
        """
        Count total files to be processed.

        Returns:
            int: Total number of files to process
        """
        total_files = 0
        for root, dirs, files in os.walk(folder_path, topdown=True):
            if self.should_stop:
                break

            # Apply directory filters
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(d, pattern) for pattern in exclude_folders
            )]
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]


            for file in files:
                if self.should_stop:
                    break

                if not include_hidden and file.startswith('.'):
                    continue

                if any(fnmatch.fnmatch(file, pattern) for pattern in exclude_files):
                    continue


                file_path = os.path.join(root, file)
                if file_path in self.processed_files:
                    continue

                file_ext = os.path.splitext(file)[1]
                if ((mode == "inclusion" and file_ext in extensions) or
                    (mode == "exclusion" and file_ext not in extensions)):
                    total_files += 1

        return total_files

    async def _process_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str],
        output_file: Any,
        total_files: int,
    ) -> int:
        """
        Process all files with progress tracking.

        Returns:
            int: Number of processed files
        """
        processed_count = 0
        for root, dirs, files in os.walk(folder_path, topdown=True):
            if self.should_stop:
                break

            # Apply directory filters
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(d, pattern) for pattern in exclude_folders
            )]
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]

            for file in files:
                if self.should_stop:
                    break

                if not include_hidden and file.startswith('.'):
                    continue

                if any(fnmatch.fnmatch(file, pattern) for pattern in exclude_files):
                    continue


                file_path = os.path.join(root, file)
                if file_path in self.processed_files:
                    continue

                file_ext = os.path.splitext(file)[1]
                if ((mode == "inclusion" and file_ext in extensions) or
                    (mode == "exclusion" and file_ext not in extensions)):

                    retry_count = 0
                    while retry_count < MAX_RETRY_ATTEMPTS:
                        try:
                            await self.process_file(file_path, output_file)
                            processed_count += 1
                            self.output_queue.put(("progress_update", (processed_count, file_path)))
                            break
                        except Exception as e:
                            retry_count += 1
                            if retry_count >= MAX_RETRY_ATTEMPTS:
                                self._handle_file_error(file_path, f"Max retries exceeded: {str(e)}")
                                break
                            else:
                                await asyncio.sleep(RETRY_DELAY)

        return processed_count

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive processing statistics.

        Returns:
            Dict[str, Any]: Dictionary containing processing statistics
        """
        if not self.start_time:
            return {}
        duration = time.time() - self.start_time
        total_size = sum(
            info.get("total_size", 0)
            for info in self.extraction_summary.values()
            if isinstance(info, dict)
        )


        processed_count = sum(info.get('count', 0) for ext, info in self.extraction_summary.items() if isinstance(info, dict))

        return {
            "duration": duration,
            "duration_formatted": format_duration(duration),
            "total_files_processed": processed_count,
            "total_size": total_size,
            "total_size_formatted": get_formatted_size(total_size),
            "failed_files_count": len(self._cache['failed_files']),
            "skipped_files_count": len(self._cache['skipped_files']),
            "extensions_processed": {
                ext: info
                for ext, info in self.extraction_summary.items()
                if isinstance(info, dict) and "count" in info
            },
            "processing_rate": processed_count / duration if duration > 0 else 0,
            "errors": list(self._cache['failed_files']),
            "warnings": list(self._cache['skipped_files'])
        }

    def cancel_processing(self) -> None:
        """Cancel ongoing processing operations."""
        self.should_stop = True
        logging.info("File processing cancelled by user")

class FileExtractorGUI:
    """Enhanced GUI with improved responsiveness, error handling, and user experience."""

    def __init__(self, master: tk.Tk):
        """Initialize GUI with enhanced error handling and features."""
        self.master = master
        self.master.title(f"{APP_NAME} v{__version__}")

        # Use dimensions from UI_CONSTANTS
        dims = UI_CONSTANTS['DIMENSIONS']

        # Get screen dimensions
        screen_width = master.winfo_screenwidth()
        screen_height = master.winfo_screenheight()

        # Calculate window size
        window_width = min(int(screen_width * dims['max_screen_ratio']), dims['width'])
        window_height = min(int(screen_height * dims['max_screen_ratio']), dims['height'])

        # Calculate center position
        position_x = (screen_width - window_width) // 2
        position_y = (screen_height - window_height) // 2

        # Set window geometry and constraints
        self.master.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        self.master.minsize(dims['min_width'], dims['min_height'])

        # Initialize components with better error handling
        try:
            # Set window icon if available
            icon_path = "icon.ico"
            if hasattr(sys, '_MEIPASS'): # PyInstaller temp folder
                icon_path = os.path.join(sys._MEIPASS, icon_path)
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)


            # Initialize configuration
            self.config = Config()

            # Setup UI state
            self.setup_variables()
            self.setup_ui_components()
            self.connect_event_handlers()

            # Initialize processing state
            self.extraction_in_progress = False
            self.loop = None
            self.thread = None
            self.start_time = None

            # Initialize tooltips if enabled
            if self.config.get('show_tooltips', True):
                self.setup_tooltips()

            # Apply initial theme
            self.apply_theme(self.config.get('theme', 'system'))

            # Set initial status
            self.update_status("Ready")

            # Start system monitor if enabled
            self.setup_system_monitor()

            # Schedule auto-save
            self.schedule_auto_save()

            # Load recent folders into menu
            self.update_recent_folders_menu()

            # Start checking the queue for messages from other threads
            self.check_queue()


        except Exception as e:
            logging.error(f"Error initializing GUI: {str(e)}", exc_info=True)
            messagebox.showerror("Initialization Error",
                               f"Error initializing application: {str(e)}")
            self.master.destroy()

    def setup_variables(self) -> None:
        """Initialize all GUI variables with proper typing."""
        # Core variables
        self.folder_path = tk.StringVar(value="")
        self.output_file_name = tk.StringVar(
            value=self.config.get('output_file', 'output.txt')
        )
        self.mode = tk.StringVar(value=self.config.get('mode', 'inclusion'))
        self.include_hidden = tk.BooleanVar(
            value=self.config.get('include_hidden', False)
        )

        # Extension variables
        self.extension_vars = {
            ext: tk.BooleanVar(value=True) for ext in COMMON_EXTENSIONS
        }
        self.custom_extensions = tk.StringVar()

        # Exclusion variables
        self.exclude_files = tk.StringVar(
            value=self.config.get('exclude_files', ', '.join(DEFAULT_EXCLUDE_FILES))
        )
        self.exclude_folders = tk.StringVar(
            value=self.config.get('exclude_folders', ', '.join(DEFAULT_EXCLUDE_FOLDERS))
        )

        # Processing variables
        self.output_queue = queue.Queue()
        self.file_processor = FileProcessor(self.output_queue, self.config)

        # Status variables
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.memory_var = tk.StringVar(value="Memory: N/A")
        self.disk_var = tk.StringVar(value="Disk: N/A")

        # Theme variables
        self.theme_var = tk.StringVar(
            value=self.config.get('theme', 'system')
        )

        # Preference variables with proper initialization
        self.show_tooltips_var = tk.BooleanVar(
            value=self.config.get('show_tooltips', True)
        )
        self.confirm_overwrite_var = tk.BooleanVar(
            value=self.config.get('confirm_overwrite', True)
        )
        self.auto_save_var = tk.BooleanVar(
            value=self.config.get('auto_save', True)
        )
        self.show_system_monitor_var = tk.BooleanVar(
            value=self.config.get('show_system_monitor', True)
        )

    def setup_ui_components(self) -> None:
        """Set up UI components with improved layout and styling."""
        try:
            # Configure root window styling
            self.master.configure(bg=UI_CONSTANTS['COLORS'].get(self.theme_var.get(), UI_CONSTANTS['COLORS']['light'])['bg'])


            # Create main container with proper padding and colors
            self.main_container = ttk.Frame(
                self.master,
                padding=UI_CONSTANTS['PADDING']['frame'],
                style='Main.TFrame'
            )
            self.main_container.grid(
                row=0, column=0,
                sticky='nsew',
                padx=UI_CONSTANTS['PADDING']['frame'],
                pady=UI_CONSTANTS['PADDING']['frame']
            )

            # Configure grid weights for responsive layout
            self.master.grid_rowconfigure(0, weight=1)
            self.master.grid_columnconfigure(0, weight=1)
            self.main_container.grid_columnconfigure(0, weight=3, uniform="panel")
            self.main_container.grid_columnconfigure(1, weight=2, uniform="panel")
            self.main_container.grid_rowconfigure(0, weight=1)


            # Create two main columns for better layout
            self.left_panel = ttk.Frame(self.main_container, style='Panel.TFrame')
            self.right_panel = ttk.Frame(self.main_container, style='Panel.TFrame')

            self.left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
            self.right_panel.grid(row=0, column=1, sticky='nsew', padx=(5, 0))

            self.left_panel.grid_rowconfigure(2, weight=1) # Allow exclusion frame to expand
            self.right_panel.grid_rowconfigure(1, weight=1) # Allow output log to expand


            # Setup sections in new order
            self.setup_input_section()
            self.setup_actions_section()
            self.setup_exclusion_fields() # Added to the left panel
            self.setup_extension_section()
            self.setup_output_section()
            self.setup_menu_bar()
            self.setup_status_bar()

            # Apply styles
            self.apply_styles()

        except Exception as e:
            logging.error(f"Error setting up UI components: {str(e)}", exc_info=True)
            raise

    def setup_input_section(self) -> None:
        """Setup input section with improved layout."""
        # Create input frame
        input_frame = ttk.LabelFrame(
            self.left_panel,
            text="Input Settings",
            padding=UI_CONSTANTS['PADDING']['frame'],
            style='Section.TLabelframe'
        )
        input_frame.grid(
            row=0, column=0,
            sticky='nsew',
            padx=UI_CONSTANTS['PADDING']['widget'],
            pady=UI_CONSTANTS['PADDING']['widget']
        )
        input_frame.grid_columnconfigure(0, weight=1)


        # Folder selection with browsing
        folder_frame = ttk.Frame(input_frame, style='Panel.TFrame')
        folder_frame.grid(row=0, column=0, sticky='ew', pady=5)
        folder_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(
            folder_frame,
            text="Folder:",
            style='Label.TLabel'
        ).grid(row=0, column=0, padx=5, sticky='w')

        ttk.Entry(
            folder_frame,
            textvariable=self.folder_path,
            style='Entry.TEntry'
        ).grid(row=0, column=1, sticky='ew', padx=5)

        button_frame = ttk.Frame(folder_frame, style='Panel.TFrame')
        button_frame.grid(row=0, column=2, padx=5)

        ttk.Button(
            button_frame,
            text="Browse",
            command=self.browse_folder,
            style='Action.TButton'
        ).pack(side='left', padx=2)

        ttk.Button(
            button_frame,
            text="▼",
            width=3,
            command=self.show_recent_folders,
            style='Tool.TButton'
        ).pack(side='left', padx=2)

        # Output file settings
        output_frame = ttk.Frame(input_frame, style='Panel.TFrame')
        output_frame.grid(row=1, column=0, sticky='ew', pady=5)
        output_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(
            output_frame,
            text="Output:",
            style='Label.TLabel'
        ).grid(row=0, column=0, padx=5, sticky='w')

        ttk.Entry(
            output_frame,
            textvariable=self.output_file_name,
            style='Entry.TEntry'
        ).grid(row=0, column=1, sticky='ew', padx=5)

        # Mode selection
        mode_frame = ttk.Frame(input_frame, style='Panel.TFrame')
        mode_frame.grid(row=2, column=0, sticky='w', pady=5)

        ttk.Label(
            mode_frame,
            text="Mode:",
            style='Label.TLabel'
        ).grid(row=0, column=0, padx=5)

        ttk.Radiobutton(
            mode_frame,
            text="Include",
            variable=self.mode,
            value="inclusion",
            style='Radio.TRadiobutton'
        ).grid(row=0, column=1, padx=15)

        ttk.Radiobutton(
            mode_frame,
            text="Exclude",
            variable=self.mode,
            value="exclusion",
            style='Radio.TRadiobutton'
        ).grid(row=0, column=2, padx=15)

        # Options
        options_frame = ttk.Frame(input_frame, style='Panel.TFrame')
        options_frame.grid(row=3, column=0, sticky='w', pady=5)

        ttk.Checkbutton(
            options_frame,
            text="Include hidden files/folders",
            variable=self.include_hidden,
            style='Check.TCheckbutton'
        ).pack(side='left', padx=5)

    def setup_exclusion_fields(self) -> None:
        """Set up exclusion pattern fields with improved layout."""
        # Create exclusion frame
        excl_frame = ttk.LabelFrame(
            self.left_panel,
            text="Exclusion Patterns",
            padding=UI_CONSTANTS['PADDING']['frame'],
            style='Section.TLabelframe'
        )
        excl_frame.grid(row=2, column=0, sticky='nsew', padx=UI_CONSTANTS['PADDING']['widget'], pady=UI_CONSTANTS['PADDING']['widget'])
        excl_frame.grid_columnconfigure(0, weight=1)

        # Files exclusion
        files_label = ttk.Label(excl_frame, text="Exclude files (comma-separated patterns):", style='Label.TLabel')
        files_label.grid(row=0, column=0, sticky='w', padx=5, pady=(0,2))
        files_entry = ttk.Entry(excl_frame, textvariable=self.exclude_files, style='Entry.TEntry')
        files_entry.grid(row=1, column=0, sticky='ew', padx=5)

        # Folders exclusion
        folders_label = ttk.Label(excl_frame, text="Exclude folders (comma-separated patterns):", style='Label.TLabel')
        folders_label.grid(row=2, column=0, sticky='w', padx=5, pady=(10,2))
        folders_entry = ttk.Entry(excl_frame, textvariable=self.exclude_folders, style='Entry.TEntry')
        folders_entry.grid(row=3, column=0, sticky='ew', padx=5)

        # Reset buttons
        reset_frame = ttk.Frame(excl_frame, style='Panel.TFrame')
        reset_frame.grid(row=4, column=0, sticky='e', pady=10)
        ttk.Button(reset_frame, text="Reset Files", command=lambda: self.reset_exclusion('files'), style='Tool.TButton').pack(side='left', padx=5)
        ttk.Button(reset_frame, text="Reset Folders", command=lambda: self.reset_exclusion('folders'), style='Tool.TButton').pack(side='left', padx=5)


    def setup_extension_section(self) -> None:
        """Setup file extension section with improved layout."""
        # Create extensions frame
        ext_frame = ttk.LabelFrame(
            self.right_panel,
            text="File Extensions",
            padding=UI_CONSTANTS['PADDING']['frame'],
            style='Section.TLabelframe'
        )
        ext_frame.grid(
            row=0, column=0,
            sticky='nsew',
            padx=UI_CONSTANTS['PADDING']['widget'],
            pady=UI_CONSTANTS['PADDING']['widget']
        )
        ext_frame.grid_columnconfigure(0, weight=1)


        # Common extensions grid
        ext_grid = ttk.Frame(ext_frame, style='Panel.TFrame')
        ext_grid.grid(row=0, column=0, sticky='nsew', pady=5)

        # Calculate optimal grid layout
        total_extensions = len(self.extension_vars)
        optimal_columns = 4
        rows = (total_extensions + optimal_columns - 1) // optimal_columns

        for i, (ext, var) in enumerate(self.extension_vars.items()):
            row = i // optimal_columns
            col = i % optimal_columns
            ttk.Checkbutton(
                ext_grid,
                text=ext,
                variable=var,
                style='Check.TCheckbutton'
            ).grid(row=row, column=col, padx=10, pady=2, sticky='w')

        # Custom extensions
        custom_frame = ttk.Frame(ext_frame, style='Panel.TFrame')
        custom_frame.grid(row=1, column=0, sticky='ew', pady=10)
        custom_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(
            custom_frame,
            text="Custom:",
            style='Label.TLabel'
        ).grid(row=0, column=0, padx=5, sticky='w')

        ttk.Entry(
            custom_frame,
            textvariable=self.custom_extensions,
            style='Entry.TEntry'
        ).grid(row=0, column=1, sticky='ew', padx=5)

        # Quick action buttons
        button_frame = ttk.Frame(ext_frame, style='Panel.TFrame')
        button_frame.grid(row=2, column=0, sticky='ew', pady=5)

        ttk.Button(
            button_frame,
            text="Select All",
            command=self.select_all_extensions,
            style='Tool.TButton'
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Clear All",
            command=self.clear_all_extensions,
            style='Tool.TButton'
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Reset to Default",
            command=self.reset_extensions,
            style='Tool.TButton'
        ).pack(side='left', padx=5)

    def setup_actions_section(self) -> None:
        """Setup action buttons section with improved layout."""
        # Create actions frame
        actions_frame = ttk.LabelFrame(
            self.left_panel,
            text="Actions",
            padding=UI_CONSTANTS['PADDING']['frame'],
            style='Section.TLabelframe'
        )
        actions_frame.grid(
            row=1, column=0,
            sticky='nsew',
            padx=UI_CONSTANTS['PADDING']['widget'],
            pady=UI_CONSTANTS['PADDING']['widget']
        )
        actions_frame.grid_columnconfigure(0, weight=1)

        # Main action buttons
        main_buttons = ttk.Frame(actions_frame, style='Panel.TFrame')
        main_buttons.grid(row=0, column=0, sticky='ew', pady=5)
        main_buttons.grid_columnconfigure(0, weight=1)
        main_buttons.grid_columnconfigure(1, weight=1)


        # Extract button with prominent styling
        self.extract_button = ttk.Button(
            main_buttons,
            text="Extract Files",
            command=self.execute,
            style='Primary.TButton'
        )
        self.extract_button.grid(row=0, column=0, sticky='ew', padx=5, pady=5)


        # Cancel button (initially disabled)
        self.cancel_button = ttk.Button(
            main_buttons,
            text="Cancel",
            command=self.cancel_extraction,
            state='disabled',
            style='Action.TButton'
        )
        self.cancel_button.grid(row=0, column=1, sticky='ew', padx=5, pady=5)

        # Progress section
        progress_frame = ttk.Frame(actions_frame, style='Panel.TFrame')
        progress_frame.grid(row=1, column=0, sticky='ew', pady=10)
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            style='Progress.Horizontal.TProgressbar'
        )
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky='ew')

        self.progress_label = ttk.Label(
            progress_frame,
            text="0%",
            style='Status.TLabel'
        )
        self.progress_label.grid(row=1, column=0, sticky='w', pady=2)

        self.timer_label = ttk.Label(
            progress_frame,
            text="Time: 00:00:00",
            style='Status.TLabel'
        )
        self.timer_label.grid(row=1, column=1, sticky='e')

    def setup_output_section(self) -> None:
        """Setup output and log section with improved layout."""
        # Create output frame
        output_frame = ttk.LabelFrame(
            self.right_panel,
            text="Output Log",
            padding=UI_CONSTANTS['PADDING']['frame'],
            style='Section.TLabelframe'
        )
        output_frame.grid(
            row=1, column=0,
            sticky='nsew',
            padx=UI_CONSTANTS['PADDING']['widget'],
            pady=UI_CONSTANTS['PADDING']['widget']
        )
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(0, weight=1)

        # Log display
        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            height=15,
            font=UI_CONSTANTS['FONTS']['default']
        )
        self.output_text.grid(row=0, column=0, sticky='nsew', pady=5)
        self.output_text.config(state='disabled')


        # Configure text tags for different message types
        theme = self.theme_var.get() if self.theme_var.get() in ['light', 'dark'] else 'light'
        colors = UI_CONSTANTS['COLORS'][theme]

        self.output_text.tag_configure("info", foreground=colors['fg'])
        self.output_text.tag_configure("error", foreground=colors['error'])
        self.output_text.tag_configure("warning", foreground=colors['warning'])
        self.output_text.tag_configure("success", foreground=colors['success'])


        # Button frame
        button_frame = ttk.Frame(output_frame, style='Panel.TFrame')
        button_frame.grid(row=1, column=0, sticky='ew', pady=5)

        ttk.Button(
            button_frame,
            text="Clear Log",
            command=self.clear_output,
            style='Tool.TButton'
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Save Log",
            command=self.save_output_log,
            style='Tool.TButton'
        ).pack(side='left', padx=5)

        ttk.Button(
            button_frame,
            text="Generate Report",
            command=self.generate_report,
            style='Tool.TButton'
        ).pack(side='right', padx=5)

    def apply_styles(self) -> None:
        """Apply custom styles to widgets."""
        style = ttk.Style()
        theme = self.theme_var.get()
        if theme == 'system':
             # A simple heuristic to guess system theme. More robust methods are platform-specific.
             try:
                 # For Windows
                 import winreg
                 key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                 theme = 'light' if winreg.QueryValueEx(key, "AppsUseLightTheme")[0] else 'dark'
             except:
                 theme = 'light' # Default for other systems

        # Get current theme colors
        colors = UI_CONSTANTS['COLORS'][theme]

        # Configure common styles
        style.configure('TFrame', background=colors['bg'])
        style.configure('Main.TFrame', background=colors['bg'])
        style.configure('Panel.TFrame', background=colors['frame_bg'])
        style.configure('Section.TLabelframe', background=colors['frame_bg'], foreground=colors['fg'], bordercolor=colors['border'])
        style.configure('Section.TLabelframe.Label', background=colors['frame_bg'], foreground=colors['fg'], font=UI_CONSTANTS['FONTS']['header'])
        style.configure('TLabel', background=colors['frame_bg'], foreground=colors['fg'], font=UI_CONSTANTS['FONTS']['default'])
        style.configure('Status.TLabel', background=colors['bg'], foreground=colors['fg'], font=UI_CONSTANTS['FONTS']['default'])
        style.configure('TRadiobutton', background=colors['frame_bg'], foreground=colors['fg'], font=UI_CONSTANTS['FONTS']['default'])
        style.configure('TCheckbutton', background=colors['frame_bg'], foreground=colors['fg'], font=UI_CONSTANTS['FONTS']['default'])


        # Button styles
        style.configure('TButton', padding=(10, 5), font=UI_CONSTANTS['FONTS']['default'])
        style.map('TButton',
            background=[('active', colors['button_hover'])],
            foreground=[('active', colors['fg'])]
        )
        style.configure('Action.TButton', background=colors['button'], foreground=colors['fg'])
        style.configure('Tool.TButton', background=colors['button'], foreground=colors['fg'], padding=5)
        style.configure('Primary.TButton', background=colors['accent'], foreground=colors['bg'], padding=(10, 5), font=UI_CONSTANTS['FONTS']['header'])
        style.map('Primary.TButton',
            background=[('active', colors['button_hover'])]
        )


        # Entry style
        style.configure('TEntry', fieldbackground=colors['input_bg'], foreground=colors['fg'], bordercolor=colors['border'])
        style.map('TEntry',
            bordercolor=[('focus', colors['accent'])],
            lightcolor=[('focus', colors['accent'])]
        )


        # Progress bar style
        style.configure('Horizontal.TProgressbar', background=colors['accent'], troughcolor=colors['frame_bg'], bordercolor=colors['border'], lightcolor=colors['accent'], darkcolor=colors['accent'])


        # Update the output text area colors
        self.output_text.config(
            background=colors['input_bg'],
            foreground=colors['fg'],
            insertbackground=colors['fg'] # cursor color
        )
        self.output_text.tag_configure("info", foreground=colors['fg'])
        self.output_text.tag_configure("error", foreground=colors['error'])
        self.output_text.tag_configure("warning", foreground=colors['warning'])
        self.output_text.tag_configure("success", foreground=colors['success'])

        self.master.configure(bg=colors['bg'])
        self.status_bar.configure(style='Status.TFrame')
        for child in self.status_bar.winfo_children():
            child.configure(style='Status.TLabel')

    def setup_status_bar(self) -> None:
        """Set up status bar with enhanced information display."""
        self.status_bar = ttk.Frame(self.master, style='Status.TFrame', padding=(5,2))
        self.status_bar.grid(row=1, column=0, sticky='ew')
        self.status_bar.grid_columnconfigure(0, weight=1)

        # Status message
        self.status_label = ttk.Label(
            self.status_bar,
            textvariable=self.status_var,
            anchor='w',
            style='Status.TLabel'
        )
        self.status_label.grid(row=0, column=0, sticky='w')

        # System resources
        resource_frame = ttk.Frame(self.status_bar, style='Status.TFrame')
        resource_frame.grid(row=0, column=1, sticky='e')

        self.memory_label = ttk.Label(
            resource_frame,
            textvariable=self.memory_var,
            anchor='e',
            style='Status.TLabel'
        )
        self.memory_label.pack(side='right', padx=5)

        self.disk_label = ttk.Label(
            resource_frame,
            textvariable=self.disk_var,
            anchor='e',
            style='Status.TLabel'
        )
        self.disk_label.pack(side='right', padx=5)


    # This method can be simplified as tooltips are complex to manage perfectly.
    # A library like `tksheet` or `tktooltip` would be better for a production app.
    def setup_tooltips(self) -> None:
        """Setup tooltips for UI elements."""
        pass # For brevity, the complex tooltip logic is omitted.
             # A proper implementation would use a helper class or library.

    def setup_system_monitor(self) -> None:
        """Setup system resource monitoring with periodic updates."""
        try:
            self.update_system_resources()
        except Exception as e:
            logging.error(f"Error setting up system monitor: {str(e)}")

    def setup_timer(self) -> None:
        """Setup processing timer with periodic updates."""
        self.start_time = time.time()
        self.update_timer()

    # Event Handlers and Core Logic
    def execute(self) -> None:
        """Execute file extraction with comprehensive error handling."""
        if self.extraction_in_progress:
            return

        try:
            self.validate_inputs()
            self.prepare_extraction()
            self.start_extraction()
        except ValueError as e:
            messagebox.showwarning("Input Error", str(e))
            self.reset_extraction_state(success=False)
        except Exception as e:
            logging.error(f"Error starting extraction: {str(e)}", exc_info=True)
            messagebox.showerror("Error", str(e))
            self.reset_extraction_state(success=False)

    def validate_inputs(self) -> None:
        """Validate all user inputs with detailed error messages."""
        # Validate folder path
        folder = self.folder_path.get()
        if not folder:
            raise ValueError("Please select a folder to process.")
        if not os.path.isdir(folder):
            raise ValueError("The selected path is not a valid folder.")

        # Validate output file
        output_file = self.output_file_name.get()
        if not output_file:
            raise ValueError("Please specify an output file name.")
        if not is_valid_file_name(os.path.basename(output_file)):
            raise ValueError("Invalid output file name. It contains illegal characters.")

        # Check if output file exists and confirm overwrite
        if (os.path.exists(output_file) and
            self.confirm_overwrite_var.get()):
            if not messagebox.askyesno(
                "Confirm Overwrite",
                f"The file '{output_file}' already exists. Do you want to overwrite it?"
            ):
                raise ValueError("Operation cancelled by user.")

        # Validate extensions selection
        selected_extensions = [
            ext for ext, var in self.extension_vars.items() if var.get()
        ]
        custom_exts = [
            ext.strip() for ext in self.custom_extensions.get().split(",")
            if ext.strip()
        ]

        if not (selected_extensions or custom_exts):
            raise ValueError("Please select or enter at least one file extension.")

        # Validate custom extensions format
        for ext in custom_exts:
            if not ext.startswith('.'):
                raise ValueError(
                    f"Invalid custom extension format: '{ext}'. "
                    "Extensions must start with a dot (e.g., '.log')."
                )

    def prepare_extraction(self) -> None:
        """Prepare for extraction process with UI updates."""
        # Clear output and reset progress
        self.clear_output()
        self.progress_var.set(0)
        self.progress_label.config(text="0%")

        # Reset processor state
        self.file_processor.clear_cache()
        self.file_processor.should_stop = False

        # Update UI state
        self.extraction_in_progress = True
        self.extract_button.config(state="disabled")
        self.cancel_button.config(state="normal")

        # Update status
        self.update_status("Preparing extraction...")

        # Save current configuration
        self.save_config()

        # Start timer
        self.setup_timer()

        # Log start of extraction
        logging.info("Starting file extraction process")
        self.add_output("Starting file extraction...", "info")

    def start_extraction(self) -> None:
        """Start the extraction process in a separate thread."""
        # Gather parameters
        params = self.get_extraction_parameters()

        # Create and start processing thread
        self.thread = threading.Thread(
            target=self.run_extraction_thread,
            args=(params,),
            daemon=True,
            name="FileProcessorThread"
        )
        self.thread.start()


    def get_extraction_parameters(self) -> dict:
        """Get all parameters needed for extraction."""
        extensions = [
            ext for ext, var in self.extension_vars.items() if var.get()
        ]
        custom_exts = [
            ext.strip() for ext in self.custom_extensions.get().split(",")
            if ext.strip()
        ]
        extensions.extend(custom_exts)

        exclude_files = [
            f.strip() for f in self.exclude_files.get().split(",")
            if f.strip()
        ]
        exclude_folders = [
            f.strip() for f in self.exclude_folders.get().split(",")
            if f.strip()
        ]

        return {
            'folder_path': self.folder_path.get(),
            'output_file_name': self.output_file_name.get(),
            'mode': self.mode.get(),
            'include_hidden': self.include_hidden.get(),
            'extensions': extensions,
            'exclude_files': exclude_files,
            'exclude_folders': exclude_folders
        }

    def run_extraction_thread(self, params: dict) -> None:
        """Run the extraction process in a separate thread."""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(
                self.file_processor.extract_files(**params)
            )
        except Exception as e:
            logging.error(f"Error in extraction thread: {str(e)}", exc_info=True)
            self.output_queue.put(("error", f"A critical error occurred in the processing thread: {str(e)}"))
            self.output_queue.put(("completion", False))
        finally:
            if self.loop:
                self.loop.close()
            self.loop = None

    def update_progress(self, processed_files: int, total_files: int, current_file: str) -> None:
        """Thread-safe method to update progress bar and status."""
        try:
            # Calculate progress percentage
            progress = (processed_files / total_files * 100) if total_files > 0 else 0
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{progress:.1f}%")
            self.update_status(f"Processing: {os.path.basename(current_file)}")

        except Exception as e:
            logging.error(f"Error updating progress: {str(e)}")


    def check_queue(self) -> None:
        """Check message queue and update GUI accordingly."""
        try:
            while True: # Process all messages in the queue
                msg = self.output_queue.get_nowait()
                msg_type, msg_data = msg

                if msg_type == "info":
                    self.add_output(msg_data, "info")
                elif msg_type == "error":
                    self.add_output(f"ERROR: {msg_data}", "error")
                elif msg_type == "warning":
                    self.add_output(f"WARNING: {msg_data}", "warning")
                elif msg_type == "success":
                    self.add_output(msg_data, "success")
                elif msg_type == "status":
                    self.update_status(msg_data)
                elif msg_type == "progress_init":
                    self.progress_bar.config(maximum=msg_data)
                elif msg_type == "progress_update":
                    processed_count, current_file = msg_data
                    total_files = self.progress_bar['maximum']
                    self.update_progress(processed_count, total_files, current_file)
                elif msg_type == "completion":
                    success = msg_data
                    self.reset_extraction_state(success=success)
                    return # Stop processing queue for this cycle after completion signal

        except queue.Empty:
            pass # No messages
        finally:
            # Reschedule the check
            self.master.after(100, self.check_queue)


    def reset_extraction_state(self, success: bool = False) -> None:
        """Reset application state after extraction."""
        self.extraction_in_progress = False
        self.extract_button.config(state="normal")
        self.cancel_button.config(state="disabled")

        if success:
            self.progress_var.set(self.progress_bar['maximum']) # Ensure it's 100%
            self.progress_label.config(text="100%")
            self.update_status("Extraction completed successfully.")
            self.add_output("Extraction process finished.", "success")

            # Update recent folders
            self.update_recent_folders()

            # Show completion message
            if self.start_time:
                elapsed_time = time.time() - self.start_time
                stats = self.file_processor.get_statistics()
                if stats:
                    messagebox.showinfo(
                        "Extraction Complete",
                        f"Processed {stats['total_files_processed']} files.\n"
                        f"Total size: {stats['total_size_formatted']}\n"
                        f"Duration: {format_duration(elapsed_time)}\n"
                        f"Average speed: {stats['processing_rate']:.1f} files/second"
                    )
        else:
            self.progress_var.set(0)
            self.progress_label.config(text="0%")
            if "cancel" in self.status_var.get().lower():
                self.update_status("Extraction cancelled.")
            else:
                self.update_status("Extraction failed. Check log for errors.")


    def cancel_extraction(self) -> None:
        """Cancel ongoing extraction with proper cleanup."""
        if self.extraction_in_progress:
            if messagebox.askyesno(
                "Confirm Cancel",
                "Are you sure you want to cancel the extraction process?"
            ):
                self.update_status("Cancelling...")
                self.file_processor.cancel_processing()
                self.extraction_in_progress = False # Prevent race conditions
                # The completion signal from the thread will handle the final state reset.


    # UI Update Methods
    def update_status(self, message: str) -> None:
        """Update status bar with message."""
        self.status_var.set(message)

    def update_system_resources(self) -> None:
        """Update system resource display with color coding."""
        try:
            mem_usage, disk_usage = check_system_resources()
            self.memory_var.set(f"Memory: {mem_usage:.1f}%")
            self.disk_var.set(f"Disk: {disk_usage:.1f}%")

            # Simple color logic - can be enhanced with ttk styles
            self.memory_label.config(foreground='red' if mem_usage > MEMORY_WARNING_THRESHOLD else 'green')
            self.disk_label.config(foreground='red' if disk_usage > DISK_WARNING_THRESHOLD else 'green')

        except Exception as e:
            logging.error(f"Error updating system resources: {str(e)}")
        finally:
            if self.master.winfo_exists():
                self.master.after(5000, self.update_system_resources)


    def update_timer(self) -> None:
        """Update elapsed time display."""
        if self.extraction_in_progress and self.start_time:
            elapsed = time.time() - self.start_time
            self.timer_label.config(text=f"Time: {format_duration(elapsed)}")
            self.master.after(1000, self.update_timer)

    # File and Folder Handling Methods
    def browse_folder(self) -> None:
        """Handle folder selection with path validation."""
        try:
            initial_dir = self.config.get('last_directory', os.path.expanduser('~'))
            folder_selected = filedialog.askdirectory(
                initialdir=initial_dir,
                title="Select Folder to Process"
            )

            if folder_selected:
                self.folder_path.set(folder_selected)
                folder_name = os.path.basename(folder_selected)

                # Suggest a unique output filename in the same directory
                output_dir = os.path.dirname(folder_selected)
                suggested_filename = create_unique_filename(output_dir, f"{folder_name}_extracted.txt")
                self.output_file_name.set(os.path.join(output_dir, suggested_filename))


                self.config.set('last_directory', folder_selected)
                self.update_recent_folders()
                logging.info(f"Selected folder: {folder_selected}")

        except Exception as e:
            logging.error(f"Error selecting folder: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"An error occurred while selecting the folder: {str(e)}")

    def show_recent_folders(self) -> None:
        """Show recent folders menu."""
        try:
            menu = tk.Menu(self.master, tearoff=0)
            recent_str = self.config.get('recent_folders', '')
            recent = [r for r in recent_str.split('|') if r]

            if recent:
                for folder in recent:
                    menu.add_command(
                        label=folder,
                        command=lambda f=folder: self.select_recent_folder(f)
                    )
                menu.add_separator()
                menu.add_command(
                    label="Clear Recent Folders",
                    command=self.clear_recent_folders
                )
            else:
                menu.add_command(label="No Recent Folders", state="disabled")

            # Show menu at the current cursor position
            menu.tk_popup(self.master.winfo_pointerx(), self.master.winfo_pointery())
        except Exception as e:
            logging.error(f"Error showing recent folders menu: {str(e)}")

    def update_recent_folders(self) -> None:
        """Update recent folders list and menu."""
        try:
            recent_str = self.config.get('recent_folders', '')
            recent = recent_str.split('|') if recent_str else []
            current = self.folder_path.get()

            if current in recent:
                recent.remove(current)

            recent.insert(0, current)
            recent = recent[:MAX_RECENT_FOLDERS]

            self.config.set('recent_folders', '|'.join(recent))
            self.update_recent_folders_menu()

        except Exception as e:
            logging.error(f"Error updating recent folders: {str(e)}")

    def update_recent_folders_menu(self) -> None:
        """Update the recent folders submenu."""
        try:
            # Check if menu exists before trying to delete from it
            if hasattr(self, 'recent_menu'):
                self.recent_menu.delete(0, tk.END)
                recent_str = self.config.get('recent_folders', '')
                recent = [r for r in recent_str.split('|') if r] # Filter out empty strings

                if recent:
                    for folder in recent:
                        self.recent_menu.add_command(
                            label=folder,
                            command=lambda f=folder: self.select_recent_folder(f)
                        )
                    self.recent_menu.add_separator()
                    self.recent_menu.add_command(
                        label="Clear Recent Folders",
                        command=self.clear_recent_folders
                    )
                else:
                    self.recent_menu.add_command(label="No Recent Folders", state="disabled")

        except Exception as e:
            logging.error(f"Error updating recent folders menu: {str(e)}")

    def select_recent_folder(self, folder: str) -> None:
        """Select a folder from the recent folders list."""
        if os.path.isdir(folder):
            self.folder_path.set(folder)
        else:
            messagebox.showwarning(
                "Folder Not Found",
                f"The folder\n{folder}\nno longer exists and will be removed from recent folders."
            )
            # Remove from recent folders
            recent_str = self.config.get('recent_folders', '')
            recent = recent_str.split('|') if recent_str else []
            if folder in recent:
                recent.remove(folder)
            self.config.set('recent_folders', '|'.join(recent))
            self.update_recent_folders_menu()

    def clear_recent_folders(self) -> None:
        """Clear the recent folders list."""
        if messagebox.askyesno(
            "Clear Recent Folders",
            "Are you sure you want to clear the recent folders list?"
        ):
            self.config.set('recent_folders', '')
            self.update_recent_folders_menu()

    def add_output(self, message: str, message_type: str = "info") -> None:
        """Add message to output area with proper formatting."""
        try:
            # Temporarily enable the widget to insert text
            self.output_text.config(state='normal')
            self.output_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n", message_type)
            self.output_text.see(tk.END)
            # Disable it again to make it read-only
            self.output_text.config(state='disabled')

            # Also log to file based on message type
            if message_type == "error":
                logging.error(message)
            elif message_type == "warning":
                logging.warning(message)
            else:
                logging.info(message)

        except Exception as e:
            logging.error(f"Error adding output: {str(e)}")

    def clear_output(self) -> None:
        """Clear output text area."""
        self.output_text.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        self.output_text.config(state='disabled')

    def save_output_log(self) -> None:
        """Save output log to file."""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt")],
                title="Save Log File"
            )

            if file_path:
                self.output_text.config(state='normal')
                content = self.output_text.get(1.0, tk.END)
                self.output_text.config(state='disabled')

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                messagebox.showinfo(
                    "Log Saved",
                    f"Log has been saved to:\n{file_path}"
                )

        except Exception as e:
            logging.error(f"Error saving log: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Error saving log: {str(e)}")

    def on_closing(self) -> None:
        """Handle application closing with proper cleanup."""
        if self.extraction_in_progress:
            if not messagebox.askyesno(
                "Confirm Exit",
                "An extraction is in progress. Are you sure you want to exit? This will cancel the current operation."
            ):
                return
            self.cancel_extraction()

        try:
            self.save_config()
            logging.info("Application closed normally.")
            self.master.destroy()
        except Exception as e:
            logging.error(f"Error during application shutdown: {str(e)}")
            self.master.destroy()


    def connect_event_handlers(self) -> None:
        """Connect all event handlers and keyboard shortcuts."""
        try:
            self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.master.bind("<Control-q>", lambda e: self.on_closing())
            self.master.bind("<Control-s>", lambda e: self.save_config(True))
            self.master.bind("<F5>", lambda e: self.execute())
            self.master.bind("<Escape>", lambda e: self.cancel_extraction())

        except Exception as e:
            logging.error(f"Error connecting event handlers: {str(e)}", exc_info=True)
            raise

    def save_config(self, show_confirmation: bool = False) -> None:
        """Save current configuration with optional confirmation."""
        try:
            # Update config with current values from UI variables
            self.config.set('output_file', self.output_file_name.get())
            self.config.set('mode', self.mode.get())
            self.config.set('include_hidden', self.include_hidden.get())
            self.config.set('exclude_files', self.exclude_files.get())
            self.config.set('exclude_folders', self.exclude_folders.get())
            self.config.set('theme', self.theme_var.get())
            self.config.set('show_tooltips', self.show_tooltips_var.get())
            self.config.set('confirm_overwrite', self.confirm_overwrite_var.get())
            self.config.set('auto_save', self.auto_save_var.get())
            self.config.set('show_system_monitor', self.show_system_monitor_var.get())

            # Force save
            self.config.save(force=True)

            if show_confirmation:
                self.add_output("Configuration saved successfully.", "success")
                messagebox.showinfo("Configuration Saved", "Configuration has been saved successfully.")

        except Exception as e:
            logging.error(f"Error saving configuration: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Error saving configuration: {str(e)}")

    def schedule_auto_save(self) -> None:
        """Schedule periodic configuration auto-save."""
        if self.master.winfo_exists() and self.auto_save_var.get():
            self.save_config(False)
            self.master.after(AUTO_SAVE_INTERVAL * 1000, self.schedule_auto_save)

    def select_all_extensions(self) -> None:
        """Select all file extensions."""
        for var in self.extension_vars.values():
            var.set(True)

    def clear_all_extensions(self) -> None:
        """Clear all file extension selections."""
        for var in self.extension_vars.values():
            var.set(False)

    def reset_extensions(self) -> None:
        """Reset extensions to default values."""
        for ext, var in self.extension_vars.items():
            var.set(True) # Default is all selected in this design
        self.custom_extensions.set("")

    def reset_exclusion(self, exclusion_type: str) -> None:
        """Reset exclusion patterns to defaults."""
        if exclusion_type == 'files':
            self.exclude_files.set(', '.join(DEFAULT_EXCLUDE_FILES))
        elif exclusion_type == 'folders':
            self.exclude_folders.set(', '.join(DEFAULT_EXCLUDE_FOLDERS))

    def setup_menu_bar(self) -> None:
        """Set up application menu bar with enhanced options."""
        try:
            self.menu_bar = tk.Menu(self.master)
            self.master.config(menu=self.menu_bar)

            # File menu
            file_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.menu_bar.add_cascade(label="File", menu=file_menu)

            self.recent_menu = tk.Menu(file_menu, tearoff=0)
            file_menu.add_cascade(label="Recent Folders", menu=self.recent_menu)
            file_menu.add_separator()
            file_menu.add_command(label="Save Configuration", command=lambda: self.save_config(True), accelerator="Ctrl+S")
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")

            # View menu
            view_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.menu_bar.add_cascade(label="View", menu=view_menu)
            theme_menu = tk.Menu(view_menu, tearoff=0)
            view_menu.add_cascade(label="Theme", menu=theme_menu)
            for theme_name in ['Light', 'Dark', 'System']:
                theme_menu.add_radiobutton(
                    label=theme_name,
                    variable=self.theme_var,
                    value=theme_name.lower(),
                    command=lambda t=theme_name.lower(): self.apply_theme(t)
                )
            # Help Menu (Example)
            help_menu = tk.Menu(self.menu_bar, tearoff=0)
            self.menu_bar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.show_about)


        except Exception as e:
            logging.error(f"Error setting up menu bar: {str(e)}", exc_info=True)
            raise

    def show_about(self) -> None:
        """Show about dialog with application information."""
        about_text = (
            f"{APP_NAME} v{__version__}\n\n"
            f"{APP_DESCRIPTION}\n\n"
            f"For support, please visit:\n{SUPPORT_URL}"
        )
        messagebox.showinfo(f"About {APP_NAME}", about_text)

    def generate_report(self) -> None:
        """Generate comprehensive extraction report."""
        if not self.file_processor.get_statistics():
            messagebox.showinfo(
                "No Data",
                "No extraction data is available. Please run an extraction first."
            )
            return

        try:
            default_name = f"extraction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_file = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialfile=default_name,
                title="Save Extraction Report"
            )

            if not report_file:
                return

            stats = self.file_processor.get_statistics()
            report = {
                "report_generated_at": datetime.now().isoformat(),
                "source_folder": self.folder_path.get(),
                "output_file": self.output_file_name.get(),
                "statistics": stats,
                "system_info": get_system_info(),
                "configuration": self.get_extraction_parameters()
            }

            with open(report_file, "w", encoding='utf-8') as f:
                json.dump(report, f, indent=4, ensure_ascii=False)

            messagebox.showinfo(
                "Report Generated",
                f"Extraction report has been saved to:\n{report_file}"
            )

        except Exception as e:
            logging.error(f"Error generating report: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Error generating report: {str(e)}")

    def apply_theme(self, theme: str) -> None:
        """Apply selected theme with proper color scheme."""
        self.theme_var.set(theme)
        self.apply_styles()


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions with logging and a user-friendly message."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

    error_message = (
        "A critical error has occurred and the application must close.\n\n"
        "Please check the 'logs/file_extractor.log' file for detailed information."
    )
    messagebox.showerror("Critical Error", error_message)
    sys.exit(1)


def main():
    """Main application entry point with enhanced error handling and initialization."""
    # Set up global exception handler
    sys.excepthook = handle_uncaught_exception

    try:
        # Configure DPI awareness for better display scaling on Windows
        if platform.system() == 'Windows':
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        logging.warning(f"Could not set DPI awareness: {e}")


    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use('clam') # A good base theme for customization

    app = FileExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()