import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
from typing import List, Dict, Any
import logging
import threading
import queue
import asyncio
import aiofiles
import json
import hashlib
from datetime import datetime
import fnmatch
import configparser

# Set up logging with rotation
from logging.handlers import RotatingFileHandler

log_handler = RotatingFileHandler(
    "file_extractor.log",
    maxBytes=1024 * 1024,  # 1MB
    backupCount=5
)
logging.basicConfig(
    handlers=[log_handler],
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Constants
COMMON_EXTENSIONS = [
    ".css",
    ".csv",
    ".db",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".log",
    ".md",
    ".py",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
]
DEFAULT_EXCLUDE = [".git", ".vscode", "__pycache__", "venv", "node_modules", ".venv"]

class Config:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load()

    def load(self):
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.set_defaults()

    def save(self):
        with open(self.config_file, 'w') as f:
            self.config.write(f)

    def set_defaults(self):
        self.config['DEFAULT'] = {
            'output_file': 'output.txt',
            'mode': 'inclusion',
            'include_hidden': 'false',
            'exclude_files': ', '.join(DEFAULT_EXCLUDE),
            'exclude_folders': ', '.join(DEFAULT_EXCLUDE),
            'theme': 'light'
        }
        self.save()

    def get(self, key, fallback=None):
        return self.config.get('DEFAULT', key, fallback=fallback)

    def set(self, key, value):
        self.config.set('DEFAULT', key, value)
        self.save()

class FileProcessor:
    def __init__(self, output_queue: queue.Queue):
        self.output_queue = output_queue
        self.extraction_summary: Dict[str, Any] = {}

    async def process_file(self, file_path: str, output_file: Any) -> None:
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                file_content = await f.read()
            
            normalized_path = os.path.normpath(file_path).replace(os.path.sep, "/")
            await output_file.write(f"{normalized_path}:\n")
            await output_file.write(file_content)
            await output_file.write("\n\n\n")

            file_ext = os.path.splitext(file_path)[1]
            file_size = os.path.getsize(file_path)
            file_hash = hashlib.md5(file_content.encode()).hexdigest()

            self._update_extraction_summary(file_ext, file_path, file_size, file_hash)

        except UnicodeDecodeError:
            logging.warning(f"Unable to decode file: {file_path}")
        except FileNotFoundError:
            logging.warning(f"File not found: {file_path}")
        except IsADirectoryError:
            logging.warning(f"Is a directory: {file_path}")
        except PermissionError:
            logging.warning(f"Permission denied: {file_path}")
        except Exception as e:
            logging.error(f"Unexpected error processing file {file_path}: {str(e)}")

    def _update_extraction_summary(self, file_ext: str, file_path: str, file_size: int, file_hash: str) -> None:
        if file_ext not in self.extraction_summary:
            self.extraction_summary[file_ext] = {"count": 0, "total_size": 0}
        self.extraction_summary[file_ext]["count"] += 1
        self.extraction_summary[file_ext]["total_size"] += file_size

        self.extraction_summary[file_path] = {
            "size": file_size,
            "hash": file_hash,
            "extension": file_ext,
        }

    async def extract_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str],
        output_file_name: str,
        progress_callback: callable
    ) -> None:
        total_files = 0
        processed_files = 0

        async with aiofiles.open(output_file_name, "w", encoding="utf-8") as output_file:
            for root, dirs, files in os.walk(folder_path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_folders)]

                files = [
                    f for f in files
                    if not any(fnmatch.fnmatch(f, pattern) for pattern in exclude_files)
                ]

                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1]

                    if (mode == "inclusion" and file_ext in extensions) or (
                        mode == "exclusion" and file_ext not in extensions
                    ):
                        total_files += 1

            for root, dirs, files in os.walk(folder_path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                dirs[:] = [d for d in dirs if not any(fnmatch.fnmatch(d, pattern) for pattern in exclude_folders)]

                files = [
                    f for f in files
                    if not any(fnmatch.fnmatch(f, pattern) for pattern in exclude_files)
                ]

                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1]

                    if (mode == "inclusion" and file_ext in extensions) or (
                        mode == "exclusion" and file_ext not in extensions
                    ):
                        await self.process_file(file_path, output_file)
                        processed_files += 1
                        await progress_callback(processed_files, total_files)

        self.output_queue.put(
            (
                "info",
                f"Extraction complete. Processed {processed_files} files. Results written to {output_file_name}.",
            )
        )

class FileExtractorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("File Extractor Pro")
        self.master.geometry("900x700")
        self.master.minsize(900, 700)

        self.config = Config()
        self.folder_path = tk.StringVar()
        self.output_file_name = tk.StringVar()
        self.mode = tk.StringVar(value=self.config.get('mode', 'inclusion'))
        self.include_hidden = tk.BooleanVar(value=self.config.get('include_hidden', 'false').lower() == 'true')
        self.extension_vars = {ext: tk.BooleanVar(value=True) for ext in COMMON_EXTENSIONS}
        self.custom_extensions = tk.StringVar()
        self.exclude_files = tk.StringVar(value=self.config.get('exclude_files', ', '.join(DEFAULT_EXCLUDE)))
        self.exclude_folders = tk.StringVar(value=self.config.get('exclude_folders', ', '.join(DEFAULT_EXCLUDE)))
        self.output_queue = queue.Queue()
        self.file_processor = FileProcessor(self.output_queue)
        self.extraction_in_progress = False
        self.loop = None
        self.thread = None

        self.create_widgets()
        self.apply_theme(self.config.get('theme', 'light'))

    def create_widgets(self):
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(10, weight=1)

        ttk.Label(main_frame, text="Select folder:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.folder_path).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(main_frame, text="Output file name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_file_name).grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(main_frame, text="Mode:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(main_frame, text="Inclusion", variable=self.mode, value="inclusion").grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(main_frame, text="Exclusion", variable=self.mode, value="exclusion").grid(row=2, column=1, sticky=tk.E, padx=5, pady=5)

        ttk.Checkbutton(main_frame, text="Include hidden files/folders", variable=self.include_hidden).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(main_frame, text="Common extensions:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        extensions_frame = ttk.Frame(main_frame)
        extensions_frame.grid(row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        for i, (ext, var) in enumerate(self.extension_vars.items()):
            ttk.Checkbutton(extensions_frame, text=ext, variable=var).grid(row=i // 7, column=i % 7, sticky=tk.W, padx=5, pady=2)

        ttk.Label(main_frame, text="Custom extensions:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.custom_extensions).grid(row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(main_frame, text="Exclude files:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.exclude_files).grid(row=6, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        ttk.Label(main_frame, text="Exclude folders:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(main_frame, textvariable=self.exclude_folders).grid(row=7, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.extract_button = ttk.Button(main_frame, text="Extract Files", command=self.execute)
        self.extract_button.grid(row=8, column=0, columnspan=3, pady=10)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5)

        self.output_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15)
        self.output_text.grid(row=10, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)

        ttk.Button(main_frame, text="Generate Report", command=self.generate_report).grid(row=11, column=0, columnspan=3, pady=10)

        # Add a status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Add a menu bar
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.master.quit)

        # Options menu
        options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Toggle Theme", command=self.toggle_theme)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.folder_path.set(folder_selected)
            # Set the output file name to match the selected folder's name
            folder_name = os.path.basename(folder_selected)
            self.output_file_name.set(f"{folder_name}.txt")

    def execute(self):
        if self.extraction_in_progress:
            return

        folder_path = self.folder_path.get()
        output_file_name = self.output_file_name.get()

        if not folder_path:
            messagebox.showerror("Error", "Please select a folder.")
            return

        mode = self.mode.get()
        include_hidden = self.include_hidden.get()
        extensions = [ext for ext, var in self.extension_vars.items() if var.get()]
        custom_exts = [ext.strip() for ext in self.custom_extensions.get().split(",") if ext.strip()]
        extensions.extend(custom_exts)
        exclude_files = [f.strip() for f in self.exclude_files.get().split(",") if f.strip()]
        exclude_folders = [f.strip() for f in self.exclude_folders.get().split(",") if f.strip()]

        self.output_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.file_processor.extraction_summary.clear()

        self.extraction_in_progress = True
        self.extract_button.config(state="disabled")
        self.status_var.set("Extraction in progress...")

        self.save_config()

        self.thread = threading.Thread(
            target=self.run_extraction_thread,
            args=(folder_path, mode, include_hidden, extensions, exclude_files, exclude_folders, output_file_name),
            daemon=True
        )
        self.thread.start()

        self.master.after(100, self.check_queue)

    def run_extraction_thread(
            self, folder_path: str, mode: str, include_hidden: bool,
            extensions: List[str], exclude_files: List[str],
            exclude_folders: List[str], output_file_name: str):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.run_extraction(folder_path, mode, include_hidden, extensions, exclude_files, exclude_folders, output_file_name))

    async def run_extraction(
            self, folder_path: str, mode: str, include_hidden: bool,
            extensions: List[str], exclude_files: List[str],
            exclude_folders: List[str], output_file_name: str) -> None:
        try:
            await self.file_processor.extract_files(
                folder_path, mode, include_hidden, extensions,
                exclude_files, exclude_folders, output_file_name,
                self.update_progress
            )
            self.output_queue.put(("info", f"Extraction complete. Results written to {output_file_name}."))
        except Exception as e:
            logging.error(f"Error during file extraction: {str(e)}")
            self.output_queue.put(("error", f"An error occurred: {str(e)}"))
        finally:
            self.extraction_in_progress = False
            self.master.after(0, lambda: self.extract_button.config(state="normal"))
            self.master.after(0, lambda: self.status_var.set("Ready"))

    async def update_progress(self, processed_files: int, total_files: int) -> None:
        progress = (processed_files / total_files) * 100 if total_files > 0 else 0
        self.master.after(0, lambda: self.progress_var.set(progress))
        self.master.after(0, lambda: self.status_var.set(f"Processing: {processed_files}/{total_files} files"))

    def check_queue(self):
        try:
            while True:
                message_type, message = self.output_queue.get_nowait()
                if message_type == "info":
                    self.output_text.insert(tk.END, message + "\n")
                elif message_type == "error":
                    self.output_text.insert(tk.END, "ERROR: " + message + "\n", "error")
                self.output_text.see(tk.END)
                self.output_text.update_idletasks()
        except queue.Empty:
            pass
        finally:
            if self.extraction_in_progress:
                self.master.after(100, self.check_queue)

    def generate_report(self):
        if not self.file_processor.extraction_summary:
            messagebox.showinfo("Info", "No extraction data available. Please run an extraction first.")
            return

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files": sum(
                ext_info["count"]
                for ext_info in self.file_processor.extraction_summary.values()
                if isinstance(ext_info, dict) and "count" in ext_info
            ),
            "total_size": sum(
                ext_info["total_size"]
                for ext_info in self.file_processor.extraction_summary.values()
                if isinstance(ext_info, dict) and "total_size" in ext_info
            ),
            "extension_summary": {
                ext: ext_info
                for ext, ext_info in self.file_processor.extraction_summary.items()
                if isinstance(ext_info, dict) and "count" in ext_info
            },
            "file_details": {
                path: details
                for path, details in self.file_processor.extraction_summary.items()
                if isinstance(details, dict) and "size" in details
            },
        }

        with open("extraction_report.json", "w") as f:
            json.dump(report, f, indent=2)

        messagebox.showinfo(
            "Report Generated",
            "Extraction report has been saved to extraction_report.json",
        )

    def save_config(self):
        self.config.set('output_file', self.output_file_name.get())
        self.config.set('mode', self.mode.get())
        self.config.set('include_hidden', str(self.include_hidden.get()))
        self.config.set('exclude_files', self.exclude_files.get())
        self.config.set('exclude_folders', self.exclude_folders.get())

    def toggle_theme(self):
        current_theme = self.config.get('theme', 'light')
        new_theme = 'dark' if current_theme == 'light' else 'light'
        self.apply_theme(new_theme)
        self.config.set('theme', new_theme)

    def apply_theme(self, theme):
        if theme == 'dark':
            self.master.tk_setPalette(
                background='#2d2d2d', foreground='#ffffff',
                activeBackground='#4d4d4d', activeForeground='#ffffff')
            self.output_text.config(bg='#1e1e1e', fg='#ffffff')
        else:
            self.master.tk_setPalette(
                background='#f0f0f0', foreground='#000000',
                activeBackground='#e0e0e0', activeForeground='#000000')
            self.output_text.config(bg='#ffffff', fg='#000000')

def main():
    root = tk.Tk()
    app = FileExtractorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()