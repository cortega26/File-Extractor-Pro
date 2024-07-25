import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, scrolledtext
from typing import List
import logging
import threading
import queue
import asyncio
import aiofiles
import json
import hashlib
from datetime import datetime

# Set up logging
logging.basicConfig(
    filename="file_extractor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Constants
COMMON_EXTENSIONS = [
    ".py",
    ".html",
    ".css",
    ".js",
    ".txt",
    ".md",
    ".json",
    ".xml",
    ".csv",
    ".yml",
]
DEFAULT_EXCLUDE = [".git", ".vscode", "__pycache__", "venv", "node_modules"]


class FileExtractorGUI:
    def __init__(self, master):
        self.master = master
        master.title("File Extractor Pro")
        master.geometry("900x700")
        master.minsize(900, 700)

        self.folder_path = tk.StringVar()
        self.mode = tk.StringVar(value="inclusion")
        self.include_hidden = tk.BooleanVar()
        self.extension_vars = {
            ext: tk.BooleanVar(value=True) for ext in COMMON_EXTENSIONS
        }
        self.custom_extensions = tk.StringVar()
        self.exclude_files = tk.StringVar(value=", ".join(DEFAULT_EXCLUDE))
        self.exclude_folders = tk.StringVar(value=", ".join(DEFAULT_EXCLUDE))
        self.output_queue = queue.Queue()
        self.extraction_summary = {}

        self.create_widgets()

    def create_widgets(self):
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(9, weight=1)

        ttk.Label(main_frame, text="Select folder:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Entry(main_frame, textvariable=self.folder_path).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        ttk.Button(main_frame, text="Browse", command=self.browse_folder).grid(
            row=0, column=2, padx=5, pady=5
        )

        ttk.Label(main_frame, text="Mode:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Radiobutton(
            main_frame, text="Inclusion", variable=self.mode, value="inclusion"
        ).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(
            main_frame, text="Exclusion", variable=self.mode, value="exclusion"
        ).grid(row=1, column=1, sticky=tk.E, padx=5, pady=5)

        ttk.Checkbutton(
            main_frame,
            text="Include hidden files/folders",
            variable=self.include_hidden,
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        ttk.Label(main_frame, text="Common extensions:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=5
        )
        extensions_frame = ttk.Frame(main_frame)
        extensions_frame.grid(
            row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )
        for i, (ext, var) in enumerate(self.extension_vars.items()):
            ttk.Checkbutton(extensions_frame, text=ext, variable=var).grid(
                row=i // 5, column=i % 5, sticky=tk.W, padx=5, pady=2
            )

        ttk.Label(main_frame, text="Custom extensions:").grid(
            row=4, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Entry(main_frame, textvariable=self.custom_extensions).grid(
            row=4, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )

        ttk.Label(main_frame, text="Exclude files:").grid(
            row=5, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Entry(main_frame, textvariable=self.exclude_files).grid(
            row=5, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )

        ttk.Label(main_frame, text="Exclude folders:").grid(
            row=6, column=0, sticky=tk.W, padx=5, pady=5
        )
        ttk.Entry(main_frame, textvariable=self.exclude_folders).grid(
            row=6, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5
        )

        ttk.Button(main_frame, text="Extract Files", command=self.execute).grid(
            row=7, column=0, columnspan=3, pady=10
        )

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.grid(
            row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=5
        )

        self.output_text = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, height=15
        )
        self.output_text.grid(
            row=9,
            column=0,
            columnspan=3,
            sticky=(tk.W, tk.E, tk.N, tk.S),
            padx=5,
            pady=5,
        )

        ttk.Button(
            main_frame, text="Generate Report", command=self.generate_report
        ).grid(row=10, column=0, columnspan=3, pady=10)

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        self.folder_path.set(folder_selected)

    def execute(self):
        folder_path = self.folder_path.get()
        if not folder_path:
            messagebox.showerror("Error", "Please select a folder.")
            return

        mode = self.mode.get()
        include_hidden = self.include_hidden.get()
        extensions = [ext for ext, var in self.extension_vars.items() if var.get()]
        custom_exts = [
            ext.strip()
            for ext in self.custom_extensions.get().split(",")
            if ext.strip()
        ]
        extensions.extend(custom_exts)
        exclude_files = [
            f.strip() for f in self.exclude_files.get().split(",") if f.strip()
        ]
        exclude_folders = [
            f.strip() for f in self.exclude_folders.get().split(",") if f.strip()
        ]

        self.output_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.extraction_summary = {}

        threading.Thread(
            target=self.run_extraction,
            args=(
                folder_path,
                mode,
                include_hidden,
                extensions,
                exclude_files,
                exclude_folders,
            ),
            daemon=True,
        ).start()
        self.master.after(100, self.check_queue)

    def run_extraction(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str],
    ) -> None:
        try:
            asyncio.run(
                self.extract_files(
                    folder_path,
                    mode,
                    include_hidden,
                    extensions,
                    exclude_files,
                    exclude_folders,
                )
            )
            self.output_queue.put(
                ("info", "Extraction complete. Results written to output.txt.")
            )
        except Exception as e:
            logging.error(f"Error during file extraction: {str(e)}")
            self.output_queue.put(("error", f"An error occurred: {str(e)}"))

    async def extract_files(
        self,
        folder_path: str,
        mode: str,
        include_hidden: bool,
        extensions: List[str],
        exclude_files: List[str],
        exclude_folders: List[str],
    ) -> None:
        total_files = 0
        processed_files = 0

        async with aiofiles.open("output.txt", "w", encoding="utf-8") as output_file:
            for root, dirs, files in os.walk(folder_path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                dirs[:] = [d for d in dirs if d not in exclude_folders]

                for file in files:
                    if file in exclude_files:
                        continue
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1]

                    if (mode == "inclusion" and file_ext in extensions) or (
                        mode == "exclusion" and file_ext not in extensions
                    ):
                        total_files += 1

            # Reset the walk to process files
            for root, dirs, files in os.walk(folder_path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                dirs[:] = [d for d in dirs if d not in exclude_folders]

                for file in files:
                    if file in exclude_files:
                        continue
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1]

                    if (mode == "inclusion" and file_ext in extensions) or (
                        mode == "exclusion" and file_ext not in extensions
                    ):
                        await self.process_file(file_path, output_file)
                        self.output_queue.put(("info", f"Processed: {file_path}"))

                        processed_files += 1
                        progress = (
                            (processed_files / total_files) * 100
                            if total_files > 0
                            else 100
                        )
                        self.progress_var.set(progress)

        self.output_queue.put(
            (
                "info",
                f"Extraction complete. Processed {processed_files} files. Results written to output.txt.",
            )
        )

    async def process_file(self, file_path: str, output_file) -> None:
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

            if file_ext not in self.extraction_summary:
                self.extraction_summary[file_ext] = {"count": 0, "total_size": 0}
            self.extraction_summary[file_ext]["count"] += 1
            self.extraction_summary[file_ext]["total_size"] += file_size

            self.extraction_summary[file_path] = {
                "size": file_size,
                "hash": file_hash,
                "extension": file_ext,
            }

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
            self.master.after(100, self.check_queue)

    def generate_report(self):
        if not self.extraction_summary:
            messagebox.showinfo(
                "Info", "No extraction data available. Please run an extraction first."
            )
            return

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_files": sum(
                ext_info["count"]
                for ext_info in self.extraction_summary.values()
                if isinstance(ext_info, dict) and "count" in ext_info
            ),
            "total_size": sum(
                ext_info["total_size"]
                for ext_info in self.extraction_summary.values()
                if isinstance(ext_info, dict) and "total_size" in ext_info
            ),
            "extension_summary": {
                ext: ext_info
                for ext, ext_info in self.extraction_summary.items()
                if isinstance(ext_info, dict) and "count" in ext_info
            },
            "file_details": {
                path: details
                for path, details in self.extraction_summary.items()
                if isinstance(details, dict) and "size" in details
            },
        }

        with open("extraction_report.json", "w") as f:
            json.dump(report, f, indent=2)

        messagebox.showinfo(
            "Report Generated",
            "Extraction report has been saved to extraction_report.json",
        )


def main():
    root = tk.Tk()
    root.style = ttk.Style()
    root.style.theme_use("clam")
    FileExtractorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
