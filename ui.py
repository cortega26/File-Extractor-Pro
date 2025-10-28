"""Tkinter GUI for File Extractor Pro."""

from __future__ import annotations

import json
import os
import tkinter as tk
from datetime import datetime
from queue import Empty
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable, Dict

from config_manager import Config
from constants import COMMON_EXTENSIONS
from logging_utils import logger
from services import ExtractorService

STATUS_QUEUE_MAX_SIZE = 256
QUEUE_IDLE_POLL_MS = 80
QUEUE_ACTIVE_POLL_MS = 20
MIN_WINDOW_WIDTH = 480
MIN_WINDOW_HEIGHT = 540


class FileExtractorGUI:
    """Enhanced GUI with improved responsiveness and error handling."""

    def __init__(self, master):
        self.master = master
        self.master.title("File Extractor Pro")
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.style = ttk.Style(self.master)

        try:
            self.config = Config()
            self.setup_variables()
            self.setup_ui_components()
            self.connect_event_handlers()
            self._configure_responsiveness()

            self.extraction_in_progress = False
            self._pending_status_message: str | None = None

            self.service = ExtractorService(
                queue_max_size=STATUS_QUEUE_MAX_SIZE,
            )
            self.output_queue = self.service.output_queue
            self.file_processor = self.service.file_processor

            self.apply_theme(self.config.get("theme", "light"))
        except Exception as exc:
            logger.critical("Failed to initialize GUI: %s", exc, exc_info=True)
            raise

    def setup_variables(self) -> None:
        """Initialize Tkinter variables."""

        self.recent_folders = list(self.config.get_recent_folders())
        initial_folder = self.recent_folders[0] if self.recent_folders else ""

        self.folder_path = tk.StringVar(value=initial_folder)
        self.output_file_name = tk.StringVar(value=self.config.get("output_file"))
        self.mode = tk.StringVar(value=self.config.get("mode", "inclusion"))
        self.include_hidden = tk.BooleanVar(
            value=self.config.get("include_hidden", "false") == "true"
        )

        self.exclude_files = tk.StringVar(value=self.config.get("exclude_files", ""))
        self.exclude_folders = tk.StringVar(
            value=self.config.get("exclude_folders", "")
        )

        self.custom_extensions = tk.StringVar()

        self.extension_vars: Dict[str, tk.BooleanVar] = {}
        for ext in COMMON_EXTENSIONS:
            default_state = ext in {".txt", ".md", ".py"}
            self.extension_vars[ext] = tk.BooleanVar(value=default_state)

        self.progress_var = tk.DoubleVar(value=0)

    def setup_ui_components(self) -> None:
        """Create all UI widgets."""

        self.main_frame = ttk.Frame(self.master, padding="10", style="Main.TFrame")
        self.main_frame.grid(row=0, column=0, sticky=tk.N + tk.S + tk.E + tk.W)

        self.main_frame.columnconfigure(0, weight=0)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=0)

        ttk.Label(self.main_frame, text="Folder Path:").grid(
            row=0, column=0, sticky=tk.W
        )
        self.folder_entry = ttk.Entry(
            self.main_frame,
            textvariable=self.folder_path,
        )
        self.folder_entry.grid(row=0, column=1, sticky=tk.W + tk.E)
        self.browse_button = ttk.Menubutton(self.main_frame, text="Browse")
        self.browse_button.grid(row=0, column=2, padx=5)
        self.browse_menu = tk.Menu(self.browse_button, tearoff=0)
        self.browse_button["menu"] = self.browse_menu
        self._refresh_recent_folders_menu()

        ttk.Label(self.main_frame, text="Output File:").grid(
            row=1, column=0, sticky=tk.W
        )
        self.output_entry = ttk.Entry(
            self.main_frame,
            textvariable=self.output_file_name,
        )
        self.output_entry.grid(row=1, column=1, sticky=tk.W + tk.E)

        ttk.Label(self.main_frame, text="Mode:").grid(row=2, column=0, sticky=tk.W)
        self.mode_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.mode_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W + tk.E)
        ttk.Radiobutton(
            self.mode_frame,
            text="Inclusion",
            value="inclusion",
            variable=self.mode,
            style="Main.TRadiobutton",
        ).grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        ttk.Radiobutton(
            self.mode_frame,
            text="Exclusion",
            value="exclusion",
            variable=self.mode,
            style="Main.TRadiobutton",
        ).grid(row=0, column=1, sticky=tk.W)

        ttk.Checkbutton(
            self.main_frame,
            text="Include Hidden Files",
            variable=self.include_hidden,
            style="Main.TCheckbutton",
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W)

        ttk.Label(self.main_frame, text="Select Extensions:").grid(
            row=4, column=0, sticky=tk.W
        )
        self.extensions_frame = ttk.Frame(self.main_frame, style="Main.TFrame")
        self.extensions_frame.grid(
            row=4,
            column=1,
            columnspan=2,
            sticky=tk.W + tk.E,
        )

        for index, (ext, var) in enumerate(self.extension_vars.items()):
            ttk.Checkbutton(
                self.extensions_frame,
                text=ext,
                variable=var,
                style="Main.TCheckbutton",
            ).grid(row=index // 4, column=index % 4, sticky=tk.W)

        ttk.Label(self.main_frame, text="Custom Extensions (comma separated):").grid(
            row=5, column=0, sticky=tk.W
        )
        self.custom_extensions_entry = ttk.Entry(
            self.main_frame,
            textvariable=self.custom_extensions,
        )
        self.custom_extensions_entry.grid(
            row=5,
            column=1,
            columnspan=2,
            sticky=tk.W + tk.E,
        )

        ttk.Label(self.main_frame, text="Exclude Files:").grid(
            row=6, column=0, sticky=tk.W
        )
        self.exclude_files_entry = ttk.Entry(
            self.main_frame,
            textvariable=self.exclude_files,
        )
        self.exclude_files_entry.grid(
            row=6,
            column=1,
            columnspan=2,
            sticky=tk.W + tk.E,
        )
        ttk.Label(self.main_frame, text="Exclude Folders:").grid(
            row=7, column=0, sticky=tk.W
        )
        self.exclude_folders_entry = ttk.Entry(
            self.main_frame,
            textvariable=self.exclude_folders,
        )
        self.exclude_folders_entry.grid(
            row=7,
            column=1,
            columnspan=2,
            sticky=tk.W + tk.E,
        )

        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            variable=self.progress_var,
            maximum=100,
            style="Main.Horizontal.TProgressbar",
        )
        self.progress_bar.grid(row=8, column=0, columnspan=3, sticky=tk.W + tk.E)

        self.extract_button = ttk.Button(
            self.main_frame,
            text="Extract",
            command=self.execute,
            style="Accent.TButton",
        )
        self.extract_button.grid(row=9, column=0, pady=10, sticky=tk.W)

        ttk.Button(self.main_frame, text="Cancel", command=self.cancel_extraction).grid(
            row=9, column=1, pady=10, sticky=tk.W
        )

        self.setup_output_area()
        self.setup_menu_bar()
        self.setup_status_bar()

    def setup_output_area(self) -> None:
        """Set up output text area with improved formatting."""

        self.output_text = scrolledtext.ScrolledText(
            self.main_frame, wrap=tk.WORD, height=15
        )
        self.output_text.grid(
            row=10,
            column=0,
            columnspan=3,
            sticky=tk.W + tk.E + tk.N + tk.S,
            padx=5,
            pady=5,
        )

        ttk.Button(
            self.main_frame,
            text="Generate Report",
            command=self.generate_report,
            style="TButton",
        ).grid(row=11, column=0, columnspan=3, pady=10)

    def setup_menu_bar(self) -> None:
        """Set up application menu bar."""

        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)

        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.master.quit)

        options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Toggle Theme", command=self.toggle_theme)

    def setup_status_bar(self) -> None:
        """Set up status bar."""

        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            self.master,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            style="Status.TLabel",
        )
        self.status_bar.grid(row=1, column=0, sticky=tk.W + tk.E)

    def _configure_responsiveness(self) -> None:
        """Configure geometry managers for responsive resizing."""

        for row_index in range(12):
            weight = 1 if row_index in {4, 10} else 0
            self.main_frame.rowconfigure(row_index, weight=weight)

        self.master.rowconfigure(1, weight=0)

        self.master.update_idletasks()
        required_width = self.master.winfo_reqwidth()
        required_height = self.master.winfo_reqheight()
        min_width = max(MIN_WINDOW_WIDTH, int(required_width * 0.6))
        min_height = max(MIN_WINDOW_HEIGHT, int(required_height * 0.6))
        self.master.minsize(min_width, min_height)

        for column_index in range(3):
            self.main_frame.columnconfigure(
                column_index, weight=1 if column_index == 1 else 0
            )

        for column_index in range(4):
            self.extensions_frame.columnconfigure(column_index, weight=1)

        for column_index in range(self.mode_frame.grid_size()[0]):
            self.mode_frame.columnconfigure(column_index, weight=1)

    def connect_event_handlers(self) -> None:
        """Connect all event handlers."""

        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.master.bind("<F5>", lambda event: self.execute())
        self.master.bind("<Escape>", lambda event: self.cancel_extraction())

    def browse_folder(self) -> None:
        """Open a folder selection dialog and update recent history."""

        try:
            folder_selected = filedialog.askdirectory()
            if folder_selected:
                self._set_selected_folder(folder_selected)
        except Exception as exc:
            logger.error("Error selecting folder: %s", exc)
            messagebox.showerror("Error", f"Error selecting folder: {exc}")

    def _set_selected_folder(self, folder_selected: str) -> None:
        """Set the selected folder, update config, and refresh UI."""

        self.folder_path.set(folder_selected)
        folder_name = os.path.basename(folder_selected)
        self.output_file_name.set(f"{folder_name}.txt")
        self._update_recent_folders(folder_selected)
        self.save_config()
        logger.info("Selected folder: %s", folder_selected)

    def _update_recent_folders(self, folder_selected: str) -> None:
        """Maintain recent folders state and refresh the dropdown menu."""

        try:
            self.config.update_recent_folders(folder_selected)
        except ValueError as exc:
            logger.error("Failed to update recent folders: %s", exc)
            return

        self.recent_folders = list(self.config.get_recent_folders())
        self._refresh_recent_folders_menu()

    def _refresh_recent_folders_menu(self) -> None:
        """Refresh the menu for recent folders."""

        if not hasattr(self, "browse_menu"):
            return

        self.browse_menu.delete(0, tk.END)
        self.browse_menu.add_command(label="Select Folder…", command=self.browse_folder)
        if self.recent_folders:
            self.browse_menu.add_separator()
        for folder in self.recent_folders:
            display_label = folder if len(folder) <= 60 else f"…{folder[-57:]}"
            self.browse_menu.add_command(
                label=display_label,
                command=self._create_recent_folder_command(folder),
            )

    def _create_recent_folder_command(self, path: str) -> Callable[[], None]:
        """Create a callback that selects the provided folder when invoked."""

        def _command() -> None:
            self._set_selected_folder(path)

        return _command

    def execute(self) -> None:
        """Execute file extraction with improved error handling."""

        if self.extraction_in_progress:
            return

        try:
            self.validate_inputs()
            self.prepare_extraction()
            self.start_extraction()
        except Exception as exc:
            logger.error("Error starting extraction: %s", exc)
            messagebox.showerror("Error", str(exc))
            self.reset_extraction_state()

    def validate_inputs(self) -> None:
        """Validate all user inputs."""

        if not self.folder_path.get():
            raise ValueError("Please select a folder.")

        if not self.output_file_name.get():
            raise ValueError("Please specify an output file name.")

        selected_extensions = [
            ext for ext, variable in self.extension_vars.items() if variable.get()
        ]
        custom_exts = [
            ext.strip()
            for ext in self.custom_extensions.get().split(",")
            if ext.strip()
        ]

        if not (selected_extensions or custom_exts):
            raise ValueError("Please select at least one file extension.")

    def prepare_extraction(self) -> None:
        """Prepare for extraction process."""

        self.output_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.file_processor.extraction_summary.clear()
        self.extraction_in_progress = True
        self._pending_status_message = None
        self.extract_button.config(state="disabled")
        self.status_var.set("Extraction in progress...")
        self.save_config()

    def start_extraction(self) -> None:
        """Start the extraction process in a separate thread."""

        folder_path = self.folder_path.get()
        output_file_name = self.output_file_name.get()
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
            folder.strip()
            for folder in self.exclude_folders.get().split(",")
            if folder.strip()
        ]

        try:
            self.service.start_extraction(
                folder_path,
                mode,
                include_hidden,
                extensions,
                exclude_files,
                exclude_folders,
                output_file_name,
                self.update_progress,
            )
        finally:
            self.master.after(QUEUE_ACTIVE_POLL_MS, self.check_queue)

    def update_progress(self, processed_files: int, total_files: int) -> None:
        """Update progress bar and status with error handling."""

        try:
            progress = (processed_files / total_files * 100) if total_files > 0 else 0
            self.master.after(0, lambda: self.progress_var.set(progress))
            self.master.after(
                0,
                lambda: self.status_var.set(
                    f"Processing: {processed_files}/{total_files} files"
                ),
            )
        except Exception as exc:
            logger.error("Error updating progress: %s", exc)

    def check_queue(self) -> None:
        """Check message queue with improved error handling."""

        drained_any = False
        try:
            while True:
                message_type, message = self.output_queue.get_nowait()
                drained_any = True
                if message_type == "info":
                    self.output_text.insert(tk.END, message + "\n", "info")
                elif message_type == "error":
                    self.output_text.insert(tk.END, "ERROR: " + message + "\n", "error")
                    logger.error(message)
                elif message_type == "state":
                    self._handle_service_state(message)
                    continue
                else:
                    logger.debug("Received unknown message type: %s", message_type)

                self.output_text.see(tk.END)
                self.output_text.update_idletasks()

        except Empty:
            pass
        finally:
            if not self.service.is_running():
                self.extraction_in_progress = False
            if self.extraction_in_progress:
                delay = QUEUE_ACTIVE_POLL_MS if drained_any else QUEUE_IDLE_POLL_MS
                self.master.after(delay, self.check_queue)
            else:
                self.reset_extraction_state()

    def _handle_service_state(self, payload: Dict[str, str]) -> None:
        """Handle terminal worker state notifications."""

        status = payload.get("status")
        result = payload.get("result")

        if status != "finished":
            logger.debug("Ignoring non-terminal state payload: %s", payload)
            return

        self.extraction_in_progress = False
        if result == "success":
            self._pending_status_message = "Extraction complete"
        elif result == "error":
            error_message = payload.get("message", "Extraction failed")
            self._pending_status_message = f"Extraction failed: {error_message}"
        else:
            self._pending_status_message = "Extraction finished"

        try:
            self.extract_button.config(state="normal")
        except Exception as exc:  # pragma: no cover - UI specific safeguard
            logger.debug("Failed to update button state: %s", exc)

    def generate_report(self) -> None:
        """Generate extraction report with improved formatting and error handling."""

        if not self.file_processor.extraction_summary:
            messagebox.showinfo(
                "Info", "No extraction data available. Please run an extraction first."
            )
            return

        try:
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

            report_file = "extraction_report.json"
            with open(report_file, "w", encoding="utf-8") as report_handle:
                json.dump(report, report_handle, indent=2, ensure_ascii=False)

            messagebox.showinfo(
                "Report Generated", f"Extraction report has been saved to {report_file}"
            )
            logger.info("Report generated successfully: %s", report_file)

        except Exception as exc:
            error_msg = f"Error generating report: {exc}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)

    def save_config(self) -> None:
        """Save current configuration with error handling."""

        try:
            self.config.set("output_file", self.output_file_name.get())
            self.config.set("mode", self.mode.get())
            self.config.set("include_hidden", str(self.include_hidden.get()))
            self.config.set("exclude_files", self.exclude_files.get())
            self.config.set("exclude_folders", self.exclude_folders.get())
            logger.debug("Configuration saved successfully")
        except Exception as exc:
            logger.error("Error saving configuration: %s", exc)

    def toggle_theme(self) -> None:
        """Toggle between light and dark themes with error handling."""

        try:
            current_theme = self.config.get("theme", "light")
            new_theme = "dark" if current_theme == "light" else "light"
            self.apply_theme(new_theme)
            self.config.set("theme", new_theme)
            logger.info("Theme changed to: %s", new_theme)
        except Exception as exc:
            logger.error("Error toggling theme: %s", exc)

    def apply_theme(self, theme: str) -> None:
        """Apply theme with better color scheme and error handling."""

        try:
            palette = self._get_theme_palette(theme)
            base_theme = palette["base_theme"]
            if base_theme in self.style.theme_names():
                self.style.theme_use(base_theme)
            else:
                self.style.theme_use("clam")

            self.master.configure(bg=palette["window_bg"])
            self.main_frame.configure(style="Main.TFrame")
            self.extensions_frame.configure(style="Main.TFrame")
            if hasattr(self, "menu_bar"):
                try:
                    self.menu_bar.configure(
                        background=palette["menu_bg"],
                        foreground=palette["menu_text"],
                        activebackground=palette["menu_active_bg"],
                        activeforeground=palette["menu_active_text"],
                    )
                    menu_end_index = self.menu_bar.index("end") or -1
                    for menu_index in range(menu_end_index + 1):
                        self.menu_bar.entryconfig(
                            menu_index,
                            background=palette["menu_bg"],
                            foreground=palette["menu_text"],
                            activebackground=palette["menu_active_bg"],
                            activeforeground=palette["menu_active_text"],
                        )
                except tk.TclError:
                    logger.debug("Menu styling not supported on this platform")

            self.style.configure("Main.TFrame", background=palette["frame_bg"])
            self.style.configure(
                "TLabel",
                background=palette["frame_bg"],
                foreground=palette["text"],
            )
            self.style.configure(
                "Status.TLabel",
                background=palette["status_bg"],
                foreground=palette["status_text"],
                relief=tk.SUNKEN,
            )
            self.status_bar.configure(style="Status.TLabel")

            self.style.configure(
                "Main.TCheckbutton",
                background=palette["frame_bg"],
                foreground=palette["text"],
            )
            self.style.map(
                "Main.TCheckbutton",
                background=[
                    ("active", palette["check_active_bg"]),
                ],
                foreground=[
                    ("disabled", palette["disabled_text"]),
                ],
            )

            self.style.configure(
                "Main.TRadiobutton",
                background=palette["frame_bg"],
                foreground=palette["text"],
            )
            self.style.map(
                "Main.TRadiobutton",
                background=[
                    ("active", palette["check_active_bg"]),
                ],
                foreground=[
                    ("disabled", palette["disabled_text"]),
                ],
            )

            self.style.configure(
                "TButton",
                background=palette["button_bg"],
                foreground=palette["button_text"],
                borderwidth=1,
            )
            self.style.map(
                "TButton",
                background=[
                    ("active", palette["button_active_bg"]),
                    ("disabled", palette["button_disabled_bg"]),
                ],
                foreground=[
                    ("disabled", palette["disabled_text"]),
                ],
            )

            self.style.configure(
                "Accent.TButton",
                background=palette["accent_bg"],
                foreground=palette["accent_text"],
                padding=(6, 4),
            )
            self.style.map(
                "Accent.TButton",
                background=[
                    ("active", palette["accent_active_bg"]),
                    ("disabled", palette["button_disabled_bg"]),
                ],
                foreground=[
                    ("disabled", palette["disabled_text"]),
                ],
            )

            self.style.configure(
                "TEntry",
                fieldbackground=palette["entry_bg"],
                background=palette["frame_bg"],
                foreground=palette["text"],
                insertcolor=palette["text"],
                borderwidth=1,
            )
            self.style.map(
                "TEntry",
                fieldbackground=[
                    ("disabled", palette["entry_disabled_bg"]),
                ],
                foreground=[
                    ("disabled", palette["disabled_text"]),
                ],
            )

            self.style.configure(
                "TCombobox",
                fieldbackground=palette["entry_bg"],
                background=palette["frame_bg"],
                foreground=palette["text"],
            )

            self.style.configure(
                "Main.Horizontal.TProgressbar",
                troughcolor=palette["progress_trough"],
                background=palette["accent_bg"],
                bordercolor=palette["frame_bg"],
                lightcolor=palette["accent_bg"],
                darkcolor=palette["accent_active_bg"],
            )

            self.output_text.config(
                bg=palette["text_area_bg"],
                fg=palette["text_area_fg"],
                insertbackground=palette["text_area_fg"],
            )
            self.output_text.tag_configure("info", foreground=palette["text_area_fg"])
            self.output_text.tag_configure("error", foreground=palette["error_text"])

            logger.debug("Theme applied: %s", theme)
        except Exception as exc:
            logger.error("Error applying theme: %s", exc)

    def _get_theme_palette(self, theme: str) -> Dict[str, str]:
        """Return palette settings for supported themes."""

        palettes: Dict[str, Dict[str, str]] = {
            "dark": {
                "base_theme": "clam",
                "window_bg": "#1b1d1f",
                "frame_bg": "#25282a",
                "text": "#f5f5f5",
                "status_bg": "#1b1d1f",
                "status_text": "#d7d7d7",
                "menu_bg": "#25282a",
                "menu_text": "#f5f5f5",
                "menu_active_bg": "#303335",
                "menu_active_text": "#ffffff",
                "check_active_bg": "#303335",
                "button_bg": "#303335",
                "button_text": "#f5f5f5",
                "button_active_bg": "#3a4044",
                "button_disabled_bg": "#2a2d2f",
                "accent_bg": "#3f72ff",
                "accent_text": "#ffffff",
                "accent_active_bg": "#335fcc",
                "entry_bg": "#1f2224",
                "entry_disabled_bg": "#2a2d2f",
                "disabled_text": "#7f868a",
                "progress_trough": "#1f2224",
                "text_area_bg": "#1f2123",
                "text_area_fg": "#f5f5f5",
                "error_text": "#ff8787",
            },
            "light": {
                "base_theme": "clam",
                "window_bg": "#e9edf2",
                "frame_bg": "#f7f9fc",
                "text": "#1f2933",
                "status_bg": "#d8dee6",
                "status_text": "#1f2933",
                "menu_bg": "#f7f9fc",
                "menu_text": "#1f2933",
                "menu_active_bg": "#dce3ef",
                "menu_active_text": "#1f2933",
                "check_active_bg": "#e1e7ef",
                "button_bg": "#e1e7ef",
                "button_text": "#1f2933",
                "button_active_bg": "#d0d7e2",
                "button_disabled_bg": "#c3c9d3",
                "accent_bg": "#3f51b5",
                "accent_text": "#ffffff",
                "accent_active_bg": "#32408f",
                "entry_bg": "#ffffff",
                "entry_disabled_bg": "#e2e6ed",
                "disabled_text": "#9aa5b1",
                "progress_trough": "#d8dee6",
                "text_area_bg": "#ffffff",
                "text_area_fg": "#1f2933",
                "error_text": "#c62828",
            },
        }
        selected_palette = palettes.get(theme, palettes["light"])
        return dict(selected_palette)

    def reset_extraction_state(self) -> None:
        """Reset the application state after extraction."""

        self.extraction_in_progress = False
        self.extract_button.config(state="normal")
        status_message = self._pending_status_message or "Ready"
        self._pending_status_message = None
        self.status_var.set(status_message)
        self.progress_var.set(0)

    def cancel_extraction(self) -> None:
        """Cancel ongoing extraction with proper cleanup."""

        if self.extraction_in_progress:
            self._pending_status_message = "Extraction cancelled"
            self.extraction_in_progress = False
            self.service.cancel()
            self.reset_extraction_state()

    def on_closing(self) -> None:
        """Handle application closing with proper cleanup."""

        if self.extraction_in_progress:
            if not messagebox.askyesno(
                "Confirm Exit",
                "An extraction is in progress. Are you sure you want to exit?",
            ):
                return
            self.cancel_extraction()

        try:
            self.save_config()
            logger.info("Application closed normally")
            self.master.destroy()
        except Exception as exc:
            logger.error("Error during application shutdown: %s", exc)
            self.master.destroy()


__all__ = ["FileExtractorGUI"]
