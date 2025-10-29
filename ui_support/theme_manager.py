"""Theme management helpers extracted from the Tkinter GUI monolith."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Dict
from tkinter import ttk


@dataclass(frozen=True)
class ThemePalette:
    """Immutable collection of palette tokens for a theme variant."""

    base_theme: str
    window_bg: str
    frame_bg: str
    text: str
    status_bg: str
    status_text: str
    menu_bg: str
    menu_text: str
    menu_active_bg: str
    menu_active_text: str
    check_active_bg: str
    button_bg: str
    button_text: str
    button_active_bg: str
    button_disabled_bg: str
    accent_bg: str
    accent_text: str
    accent_active_bg: str
    entry_bg: str
    entry_disabled_bg: str
    disabled_text: str
    progress_trough: str
    text_area_bg: str
    text_area_fg: str
    error_text: str
    banner_info_bg: str
    banner_info_text: str
    banner_success_bg: str
    banner_success_text: str
    banner_warning_bg: str
    banner_warning_text: str
    banner_error_bg: str
    banner_error_text: str


@dataclass
class ThemeTargets:
    """Describe the widgets that require palette updates."""

    master: tk.Misc
    main_frame: ttk.Frame
    extensions_frame: ttk.Frame
    status_bar: ttk.Label
    output_text: tk.Text
    menu_bar: tk.Menu | None = None


# Fix: Q-103
class ThemeManager:
    """Apply colour palettes consistently across Tkinter widgets."""

    def __init__(self, style: ttk.Style, targets: ThemeTargets) -> None:
        self._style = style
        self._targets = targets
        self._palettes = self._build_palettes()
        self._active_theme = "light"
        self._active_palette = self._palettes[self._active_theme]

    def apply(self, theme: str) -> None:
        """Apply the requested theme to the registered widgets."""

        palette = self._palettes.get(theme, self._palettes["light"])
        self._active_theme = theme if theme in self._palettes else "light"
        self._active_palette = palette
        self._apply_base_theme(palette)
        self._apply_menu_palette(palette)
        self._apply_style_palette(palette)
        self._apply_text_palette(palette)

    def active_palette(self) -> ThemePalette:
        """Return the palette currently applied to the GUI."""

        return self._active_palette

    def update_targets(self, targets: ThemeTargets) -> None:
        """Refresh widget references when the GUI rebuilds components."""

        self._targets = targets

    def _apply_base_theme(self, palette: ThemePalette) -> None:
        base_theme = palette.base_theme
        if base_theme in self._style.theme_names():
            self._style.theme_use(base_theme)
        else:
            self._style.theme_use("clam")

        self._targets.master.configure(bg=palette.window_bg)
        self._targets.main_frame.configure(style="Main.TFrame")
        self._targets.extensions_frame.configure(style="Main.TFrame")

    def _apply_menu_palette(self, palette: ThemePalette) -> None:
        menu_bar = self._targets.menu_bar
        if menu_bar is None:
            return

        try:
            menu_bar.configure(
                background=palette.menu_bg,
                foreground=palette.menu_text,
                activebackground=palette.menu_active_bg,
                activeforeground=palette.menu_active_text,
            )
            end_index = menu_bar.index("end") or -1
            for index in range(end_index + 1):
                menu_bar.entryconfig(
                    index,
                    background=palette.menu_bg,
                    foreground=palette.menu_text,
                    activebackground=palette.menu_active_bg,
                    activeforeground=palette.menu_active_text,
                )
        except tk.TclError:
            # Menu styling is platform dependent (e.g. macOS native menus).
            return

    def _apply_style_palette(self, palette: ThemePalette) -> None:
        style = self._style
        style.configure("Main.TFrame", background=palette.frame_bg)
        style.configure("TLabel", background=palette.frame_bg, foreground=palette.text)
        style.configure(
            "Status.TLabel",
            background=palette.status_bg,
            foreground=palette.status_text,
            relief=tk.SUNKEN,
        )
        self._targets.status_bar.configure(style="Status.TLabel")

        style.configure(
            "Main.TLabelframe",
            background=palette.frame_bg,
            foreground=palette.text,
        )
        style.configure(
            "Main.TLabelframe.Label",
            background=palette.frame_bg,
            foreground=palette.text,
        )

        style.configure(
            "Banner.Info.TLabel",
            background=palette.banner_info_bg,
            foreground=palette.banner_info_text,
            padding=(8, 4),
        )
        style.configure(
            "Banner.Success.TLabel",
            background=palette.banner_success_bg,
            foreground=palette.banner_success_text,
            padding=(8, 4),
        )
        style.configure(
            "Banner.Warning.TLabel",
            background=palette.banner_warning_bg,
            foreground=palette.banner_warning_text,
            padding=(8, 4),
        )
        style.configure(
            "Banner.Error.TLabel",
            background=palette.banner_error_bg,
            foreground=palette.banner_error_text,
            padding=(8, 4),
        )
        style.configure(
            "Banner.Detail.TLabel",
            background=palette.banner_info_bg,
            foreground=palette.banner_info_text,
            padding=(8, 0),
            font=("TkDefaultFont", 9),
        )

        style.configure(
            "Main.TCheckbutton",
            background=palette.frame_bg,
            foreground=palette.text,
        )
        style.map(
            "Main.TCheckbutton",
            background=[("active", palette.check_active_bg)],
            foreground=[("disabled", palette.disabled_text)],
        )

        style.configure(
            "Main.TRadiobutton",
            background=palette.frame_bg,
            foreground=palette.text,
        )
        style.map(
            "Main.TRadiobutton",
            background=[("active", palette.check_active_bg)],
            foreground=[("disabled", palette.disabled_text)],
        )

        style.configure(
            "TButton",
            background=palette.button_bg,
            foreground=palette.button_text,
            borderwidth=1,
        )
        style.map(
            "TButton",
            background=[
                ("active", palette.button_active_bg),
                ("disabled", palette.button_disabled_bg),
            ],
            foreground=[("disabled", palette.disabled_text)],
        )

        style.configure(
            "Accent.TButton",
            background=palette.accent_bg,
            foreground=palette.accent_text,
            borderwidth=1,
        )
        style.map(
            "Accent.TButton",
            background=[("active", palette.accent_active_bg)],
            foreground=[("disabled", palette.disabled_text)],
        )

        style.configure(
            "TEntry",
            fieldbackground=palette.entry_bg,
            background=palette.frame_bg,
            foreground=palette.text,
            insertcolor=palette.text,
            borderwidth=1,
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", palette.entry_disabled_bg)],
            foreground=[("disabled", palette.disabled_text)],
        )

        style.configure(
            "TCombobox",
            fieldbackground=palette.entry_bg,
            background=palette.frame_bg,
            foreground=palette.text,
        )

        style.configure(
            "Main.Horizontal.TProgressbar",
            troughcolor=palette.progress_trough,
            background=palette.accent_bg,
            bordercolor=palette.frame_bg,
            lightcolor=palette.accent_bg,
            darkcolor=palette.accent_active_bg,
        )

    def _apply_text_palette(self, palette: ThemePalette) -> None:
        text_widget = self._targets.output_text
        text_widget.config(
            bg=palette.text_area_bg,
            fg=palette.text_area_fg,
            insertbackground=palette.text_area_fg,
        )
        text_widget.tag_configure("info", foreground=palette.text_area_fg)
        text_widget.tag_configure("error", foreground=palette.error_text)

    def _build_palettes(self) -> Dict[str, ThemePalette]:
        dark_palette = ThemePalette(
            base_theme="clam",
            window_bg="#1b1d1f",
            frame_bg="#25282a",
            text="#f5f5f5",
            status_bg="#1b1d1f",
            status_text="#d7d7d7",
            menu_bg="#25282a",
            menu_text="#f5f5f5",
            menu_active_bg="#303335",
            menu_active_text="#ffffff",
            check_active_bg="#303335",
            button_bg="#303335",
            button_text="#f5f5f5",
            button_active_bg="#3a4044",
            button_disabled_bg="#2a2d2f",
            accent_bg="#3f72ff",
            accent_text="#ffffff",
            accent_active_bg="#335fcc",
            entry_bg="#1f2224",
            entry_disabled_bg="#2a2d2f",
            disabled_text="#7f868a",
            progress_trough="#1f2224",
            text_area_bg="#1f2123",
            text_area_fg="#f5f5f5",
            error_text="#ff8787",
            banner_info_bg="#1f3a5f",
            banner_info_text="#d6e6ff",
            banner_success_bg="#1f4d2b",
            banner_success_text="#d4f5dd",
            banner_warning_bg="#5f3f1f",
            banner_warning_text="#ffe8c2",
            banner_error_bg="#5f1f28",
            banner_error_text="#ffd6d6",
        )

        light_palette = ThemePalette(
            base_theme="clam",
            window_bg="#e9edf2",
            frame_bg="#f7f9fc",
            text="#1f2933",
            status_bg="#d8dee6",
            status_text="#1f2933",
            menu_bg="#f7f9fc",
            menu_text="#1f2933",
            menu_active_bg="#dce3ef",
            menu_active_text="#1f2933",
            check_active_bg="#e1e7ef",
            button_bg="#e1e7ef",
            button_text="#1f2933",
            button_active_bg="#d0d7e2",
            button_disabled_bg="#c3c9d3",
            accent_bg="#3f51b5",
            accent_text="#ffffff",
            accent_active_bg="#32408f",
            entry_bg="#ffffff",
            entry_disabled_bg="#e2e6ed",
            disabled_text="#9aa5b1",
            progress_trough="#d8dee6",
            text_area_bg="#ffffff",
            text_area_fg="#1f2933",
            error_text="#c62828",
            banner_info_bg="#dbeafe",
            banner_info_text="#1e3a8a",
            banner_success_bg="#dcfce7",
            banner_success_text="#166534",
            banner_warning_bg="#fef3c7",
            banner_warning_text="#92400e",
            banner_error_bg="#fee2e2",
            banner_error_text="#7f1d1d",
        )

        return {"dark": dark_palette, "light": light_palette}


__all__ = ["ThemeManager", "ThemeTargets", "ThemePalette"]

