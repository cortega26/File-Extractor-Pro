"""Tkinter GUI for File Extractor Pro."""

from __future__ import annotations

import os
import tkinter as tk
from dataclasses import dataclass
from queue import Empty
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Callable, Dict, List

from ui_support import StatusBanner, ThemeManager, ThemeTargets

from config_manager import Config
from constants import COMMON_EXTENSIONS
from logging_utils import logger
from processor import FileProcessor
from services import ExtractionRequest, ExtractorService

STATUS_QUEUE_MAX_SIZE = 256
QUEUE_IDLE_POLL_MS = 80
QUEUE_ACTIVE_POLL_MS = 20
MIN_WINDOW_WIDTH = 480
MIN_WINDOW_HEIGHT = 540
COMPACT_WIDTH_THRESHOLD = 760
HIGH_SCALING_THRESHOLD = 1.3


@dataclass(frozen=True)
class LayoutProfile:
    """Responsive layout configuration used by the GUI."""

    min_width: int
    min_height: int
    main_column_weights: tuple[int, int, int]
    row_weights: Dict[int, int]
    extension_columns: int
    mode_columns: int
    padding: tuple[int, int]


def calculate_layout_profile(
    *,
    width: int,
    height: int,
    required_width: int,
    required_height: int,
    scaling: float,
) -> LayoutProfile:
    """Determine the layout profile given the current window metrics."""

    compact_layout = (
        width <= COMPACT_WIDTH_THRESHOLD or scaling >= HIGH_SCALING_THRESHOLD
    )
    width_factor = 0.9 if compact_layout else 0.75
    height_factor = 0.9 if compact_layout else 0.7

    min_width = max(required_width, int(width * width_factor))
    min_height = max(required_height, int(height * height_factor))

    main_column_weights = (1, 1, 1) if compact_layout else (0, 1, 0)
    row_weights: Dict[int, int] = {11: 2, 4: 1}
    if compact_layout:
        row_weights[5] = 1

    extension_columns = 2 if compact_layout else 4
    mode_columns = 1 if compact_layout else 2
    padding = (14, 12) if compact_layout else (10, 10)

    return LayoutProfile(
        min_width=min_width,
        min_height=min_height,
        main_column_weights=main_column_weights,
        row_weights=row_weights,
        extension_columns=extension_columns,
        mode_columns=mode_columns,
        padding=padding,
    )


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
            self.theme_manager = ThemeManager(
                self.style,
                ThemeTargets(
                    master=self.master,
                    main_frame=self.main_frame,
                    extensions_frame=self.extensions_frame,
                    status_bar=self.status_bar,
                    output_text=self.output_text,
                    menu_bar=getattr(self, "menu_bar", None),
                ),
            )
            self._current_layout_profile: LayoutProfile | None = None
            self.connect_event_handlers()
            self._configure_responsiveness()

            self.extraction_in_progress = False
            self._pending_status_message: str | None = None
            self._accelerator_callbacks: list[Callable[[tk.Event], str]] = []
            self._progress_animation_running = False
            self._last_progress_value: float = 0.0

            max_file_size_mb = int(self.config.get_typed("max_memory_mb"))

            # Fix: Q-105
            def _build_processor(queue, limit=max_file_size_mb) -> FileProcessor:
                return FileProcessor(queue, max_file_size_mb=limit)

            self.service = ExtractorService(
                queue_max_size=STATUS_QUEUE_MAX_SIZE,
                file_processor_factory=_build_processor,
            )
            self.output_queue = self.service.output_queue

            initial_theme = self.config.get("theme", "light")
            self.apply_theme(initial_theme)
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
        self.mode_buttons: List[ttk.Radiobutton] = []
        for text, value in (("Inclusion", "inclusion"), ("Exclusion", "exclusion")):
            radio_button = ttk.Radiobutton(
                self.mode_frame,
                text=text,
                value=value,
                variable=self.mode,
                style="Main.TRadiobutton",
            )
            self.mode_buttons.append(radio_button)

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

        self.extension_checkbuttons: List[ttk.Checkbutton] = []
        for ext, var in self.extension_vars.items():
            check_button = ttk.Checkbutton(
                self.extensions_frame,
                text=ext,
                variable=var,
                style="Main.TCheckbutton",
            )
            self.extension_checkbuttons.append(check_button)

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

        self._build_actions_row(row=9)

        self.setup_output_area(start_row=10)
        self.setup_menu_bar()
        self.setup_status_bar()
        self._register_keyboard_shortcuts()

        self._arrange_extension_checkbuttons(columns=4)
        self._arrange_mode_buttons(columns=2)

        # Fix: Q-102 - ensure the progress bar starts in determinate mode.
        self.progress_bar.configure(mode="determinate")

    # Fix: ux_accessibility_status_banner
    def setup_output_area(self, *, start_row: int) -> None:
        """Set up output text area with an accessible status banner."""

        self.status_banner = StatusBanner(self.main_frame)
        self.status_banner.grid(
            row=start_row,
            column=0,
            columnspan=3,
            sticky=tk.W + tk.E,
            padx=5,
            pady=(8, 0),
        )
        self.status_banner.hide()

        self.output_text = scrolledtext.ScrolledText(
            self.main_frame, wrap=tk.WORD, height=15
        )
        self.output_text.grid(
            row=start_row + 1,
            column=0,
            columnspan=3,
            sticky=tk.W + tk.E + tk.N + tk.S,
            padx=5,
            pady=5,
        )

    # Fix: Q-107
    def _build_actions_row(self, row: int) -> None:
        """Create a grouped action row with predictable focus order."""

        self.actions_frame = ttk.LabelFrame(
            self.main_frame,
            text="Actions",
            style="Main.TLabelframe",
        )
        self.actions_frame.grid(
            row=row,
            column=0,
            columnspan=3,
            sticky=tk.W + tk.E,
            padx=5,
            pady=(10, 0),
        )
        self.actions_frame.columnconfigure(0, weight=0)
        self.actions_frame.columnconfigure(1, weight=0)
        self.actions_frame.columnconfigure(2, weight=1)

        self.extract_button = ttk.Button(
            self.actions_frame,
            text="Extract",
            command=self.execute,
            style="Accent.TButton",
            takefocus=True,
        )
        self.extract_button.grid(row=0, column=0, padx=(10, 5), pady=10, sticky=tk.W)
        self.extract_button.configure(underline=0)

        self.cancel_button = ttk.Button(
            self.actions_frame,
            text="Cancel",
            command=self.cancel_extraction,
            takefocus=True,
        )
        self.cancel_button.grid(row=0, column=1, padx=5, pady=10, sticky=tk.W)
        self.cancel_button.configure(underline=0)

        self.generate_report_button = ttk.Button(
            self.actions_frame,
            text="Generate Report",
            command=self.generate_report,
            style="TButton",
            takefocus=True,
        )
        self.generate_report_button.grid(
            row=0,
            column=2,
            padx=(5, 10),
            pady=10,
            sticky=tk.E,
        )
        self.generate_report_button.configure(underline=0)

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

    # Fix: Q-107
    def _register_keyboard_shortcuts(self) -> None:
        """Bind Alt-based accelerators and surface their availability."""

        shortcut_actions: dict[str, Callable[[], None]] = {
            "<Alt-e>": self.execute,
            "<Alt-E>": self.execute,
            "<Alt-c>": self.cancel_extraction,
            "<Alt-C>": self.cancel_extraction,
            "<Alt-g>": self.generate_report,
            "<Alt-G>": self.generate_report,
        }

        for sequence, action in shortcut_actions.items():
            callback = self._create_shortcut_handler(action)
            self._accelerator_callbacks.append(callback)
            self.master.bind_all(sequence, callback, add="+")

        if not self.status_var.get():
            self.status_var.set(
                "Shortcuts: Alt+E Extract, Alt+C Cancel, Alt+G Generate Report"
            )

    def _create_shortcut_handler(
        self, action: Callable[[], None]
    ) -> Callable[[tk.Event], str]:
        """Wrap action callbacks so they can be bound as Tk event handlers."""

        def handler(event: tk.Event) -> str:  # type: ignore[valid-type]
            if action is self.execute and self.extraction_in_progress:
                return "break"
            action()
            return "break"

        return handler

    def _configure_responsiveness(self) -> None:
        """Configure geometry managers for responsive resizing."""

        self.master.rowconfigure(1, weight=0)
        profile = self._determine_layout_profile()
        self._apply_layout_profile(profile)
        self.master.bind("<Configure>", self._handle_root_resize, add="+")

    def _determine_layout_profile(self) -> LayoutProfile:
        """Compute the active layout profile based on window geometry."""

        self.master.update_idletasks()
        width = max(self.master.winfo_width(), MIN_WINDOW_WIDTH)
        height = max(self.master.winfo_height(), MIN_WINDOW_HEIGHT)
        required_width = max(self.master.winfo_reqwidth(), MIN_WINDOW_WIDTH)
        required_height = max(self.master.winfo_reqheight(), MIN_WINDOW_HEIGHT)
        try:
            scaling = float(self.master.tk.call("tk", "scaling"))
        except tk.TclError:
            scaling = 1.0

        return calculate_layout_profile(
            width=width,
            height=height,
            required_width=required_width,
            required_height=required_height,
            scaling=scaling,
        )

    def _apply_layout_profile(self, profile: LayoutProfile) -> None:
        """Apply layout weights and geometry adjustments for the given profile."""

        if self._current_layout_profile == profile:
            return

        self._current_layout_profile = profile

        self.master.minsize(profile.min_width, profile.min_height)
        self.main_frame.configure(padding=profile.padding)

        for column_index, weight in enumerate(profile.main_column_weights):
            self.main_frame.columnconfigure(column_index, weight=weight)

        for row_index in range(12):
            weight = profile.row_weights.get(row_index, 0)
            self.main_frame.rowconfigure(row_index, weight=weight)

        for column_index in range(6):
            weight = 1 if column_index < profile.extension_columns else 0
            self.extensions_frame.columnconfigure(column_index, weight=weight)

        for column_index in range(4):
            weight = 1 if column_index < profile.mode_columns else 0
            self.mode_frame.columnconfigure(column_index, weight=weight)

        self._arrange_extension_checkbuttons(profile.extension_columns)
        self._arrange_mode_buttons(profile.mode_columns)

    def _handle_root_resize(self, event: tk.Event) -> None:
        """Recompute the layout profile when the window dimensions change."""

        if event.widget is not self.master:
            return

        profile = self._determine_layout_profile()
        self._apply_layout_profile(profile)

    def _arrange_extension_checkbuttons(self, columns: int) -> None:
        """Arrange extension checkbuttons based on the available columns."""

        effective_columns = max(1, columns)
        for button in self.extension_checkbuttons:
            button.grid_forget()

        for index, button in enumerate(self.extension_checkbuttons):
            row_index = index // effective_columns
            column_index = index % effective_columns
            button.grid(
                row=row_index,
                column=column_index,
                sticky=tk.W,
                padx=(0, 8),
                pady=(0, 4),
            )

    def _arrange_mode_buttons(self, columns: int) -> None:
        """Arrange mode radio buttons for the given number of columns."""

        effective_columns = max(1, columns)
        for button in self.mode_buttons:
            button.grid_forget()

        for index, button in enumerate(self.mode_buttons):
            row_index = index // effective_columns
            column_index = index % effective_columns
            button.grid(row=row_index, column=column_index, sticky=tk.W, padx=(0, 10))

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
        self._last_progress_value = 0.0
        self._ensure_progress_indeterminate()
        self.service.reset_state()
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

        request = ExtractionRequest(
            folder_path=folder_path,
            mode=mode,
            include_hidden=include_hidden,
            extensions=tuple(extensions),
            exclude_files=tuple(exclude_files),
            exclude_folders=tuple(exclude_folders),
            output_file_name=output_file_name,
        )

        try:
            self.service.start_extraction(
                request=request,
                progress_callback=self.update_progress,
            )
        finally:
            self.master.after(QUEUE_ACTIVE_POLL_MS, self.check_queue)

    def update_progress(self, processed_files: int, total_files: int) -> None:
        """Update progress bar and status with error handling."""

        try:

            def apply_update() -> None:
                try:
                    if total_files > 0:
                        self._ensure_progress_determinate()
                        progress = (processed_files / total_files) * 100
                        progress = max(self._last_progress_value, min(progress, 100.0))
                    else:
                        self._ensure_progress_indeterminate()
                        progress = max(self._last_progress_value, 0.0)

                    self.progress_var.set(progress)
                    self._last_progress_value = progress
                    self.status_var.set(
                        f"Processing: {processed_files}/{total_files} files"
                    )
                except Exception as exc_inner:  # pragma: no cover - defensive logging
                    logger.error("Error applying progress update: %s", exc_inner)

            self.master.after(0, apply_update)
        except Exception as exc:
            logger.error("Error scheduling progress update: %s", exc)

    # Fix: Q-102
    def _ensure_progress_indeterminate(self) -> None:
        """Switch the progress bar to indeterminate mode with animation."""

        if self.progress_bar.cget("mode") != "indeterminate":
            self.progress_bar.configure(mode="indeterminate")
        if not self._progress_animation_running:
            self.progress_bar.start(10)
            self._progress_animation_running = True

    # Fix: Q-102
    def _ensure_progress_determinate(self) -> None:
        """Ensure determinate mode is active and stop indeterminate animation."""

        if self._progress_animation_running:
            self.progress_bar.stop()
            self._progress_animation_running = False
        if self.progress_bar.cget("mode") != "determinate":
            self.progress_bar.configure(mode="determinate")

    def check_queue(self) -> None:
        """Check message queue with improved error handling."""

        drained_any = False
        try:
            while True:
                message_type, message = self.output_queue.get_nowait()
                drained_any = True
                if message_type == "info":
                    self.output_text.insert(tk.END, message + "\n", "info")
                    self._display_banner_message("info", message)
                elif message_type == "error":
                    self.output_text.insert(tk.END, "ERROR: " + message + "\n", "error")
                    logger.error(message)
                    self._display_banner_message("error", message)
                elif message_type == "warning":
                    warning_text = str(message)
                    self.output_text.insert(
                        tk.END, "WARNING: " + warning_text + "\n", "info"
                    )
                    logger.warning(warning_text)
                    self._display_banner_message("warning", warning_text)
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
            self.status_banner.show_success(self._pending_status_message)
        elif result == "error":
            error_message = payload.get("message", "Extraction failed")
            self._pending_status_message = f"Extraction failed: {error_message}"
            self.status_banner.show_error(self._pending_status_message)
        else:
            self._pending_status_message = "Extraction finished"
            self.status_banner.show(self._pending_status_message, severity="info")

        try:
            self.extract_button.config(state="normal")
        except Exception as exc:  # pragma: no cover - UI specific safeguard
            logger.debug("Failed to update button state: %s", exc)

    # Fix: ux_accessibility_status_banner
    def _display_banner_message(self, level: str, payload: object) -> None:
        """Surface contextual feedback in the status banner."""

        message = str(payload).strip()
        if not message:
            return

        if level == "error":
            self.status_banner.show_error(message)
        elif level == "warning":
            self.status_banner.show_warning(message)
        elif level == "info":
            lowered = message.lower()
            if "extraction" in lowered or "report" in lowered:
                self.status_banner.show(message, severity="info")

    def generate_report(self) -> None:
        """Generate extraction report with improved formatting and error handling."""

        try:
            summary = self.service.get_summary()
            if summary.total_files == 0 and not summary.file_details:
                messagebox.showinfo(
                    "Info",
                    "No extraction data available. Please run an extraction first.",
                )
                return

            report_file = self.service.generate_report()
            messagebox.showinfo(
                "Report Generated", f"Extraction report has been saved to {report_file}"
            )

        except Exception as exc:
            error_msg = f"Error generating report: {exc}"
            logger.error(error_msg)
            messagebox.showerror("Error", error_msg)

    def save_config(self) -> None:
        """Save current configuration with error handling."""

        try:
            updates = {
                "output_file": self.output_file_name.get(),
                "mode": self.mode.get(),
                "include_hidden": self.include_hidden.get(),
                "exclude_files": self.exclude_files.get(),
                "exclude_folders": self.exclude_folders.get(),
            }
            self.config.update_settings(updates)
            logger.debug("Configuration saved successfully")
        except ValueError as exc:
            logger.warning("Invalid configuration values: %s", exc)
            messagebox.showerror(
                "Configuration Error",
                f"Failed to save settings: {exc}",
            )
        except Exception as exc:
            logger.error("Error saving configuration: %s", exc)
            messagebox.showerror(
                "Configuration Error",
                "An unexpected error occurred while saving settings.",
            )

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
        """Apply theme using the extracted theme manager."""

        try:
            self.theme_manager.update_targets(
                ThemeTargets(
                    master=self.master,
                    main_frame=self.main_frame,
                    extensions_frame=self.extensions_frame,
                    status_bar=self.status_bar,
                    output_text=self.output_text,
                    menu_bar=getattr(self, "menu_bar", None),
                )
            )
            self.theme_manager.apply(theme)
            palette = self.theme_manager.active_palette()
            self.status_banner.apply_palette(palette)
            self.status_banner.clear()
            logger.debug("Theme applied: %s", theme)
        except Exception as exc:
            logger.error("Error applying theme: %s", exc)

    def reset_extraction_state(self) -> None:
        """Reset the application state after extraction."""

        self.extraction_in_progress = False
        self.extract_button.config(state="normal")
        status_message = self._pending_status_message or "Ready"
        self._pending_status_message = None
        self.status_var.set(status_message)
        self.progress_var.set(0)
        self._last_progress_value = 0.0
        self._ensure_progress_determinate()

    def cancel_extraction(self) -> None:
        """Cancel ongoing extraction with proper cleanup."""

        if self.extraction_in_progress:
            self._pending_status_message = "Extraction cancelled"
            self.extraction_in_progress = False
            self.service.cancel()
            self.reset_extraction_state()
            self.status_banner.show_warning("Extraction cancelled by user")

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
