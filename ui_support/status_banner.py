"""Accessible status banner for contextual extraction feedback."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Literal
from tkinter import ttk

from ui_support.theme_manager import ThemePalette

Severity = Literal["info", "success", "warning", "error"]


@dataclass(frozen=True)
class StatusStyle:
    """Describe palette fragments for a specific banner severity."""

    background: str
    foreground: str


# Fix: ux_accessibility_status_banner
class StatusBanner(ttk.Frame):
    """Display accessible status messages with severity-aware styling."""

    def __init__(self, master: tk.Misc, *, padding: tuple[int, int] = (8, 4)) -> None:
        super().__init__(master)
        self._styles: dict[Severity, StatusStyle] = {}
        self.columnconfigure(0, weight=1)

        self._message_var = tk.StringVar(value="Ready")
        self._detail_var = tk.StringVar(value="")
        self._label = ttk.Label(self, textvariable=self._message_var, anchor=tk.W)
        self._label.grid(row=0, column=0, sticky=tk.W + tk.E, padx=padding, pady=padding)

        self._detail_label = ttk.Label(
            self,
            textvariable=self._detail_var,
            anchor=tk.W,
            wraplength=520,
            style="Banner.Detail.TLabel",
        )
        self._detail_label.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky=tk.W,
            padx=padding,
            pady=(0, padding[1]),
        )
        self._detail_label.grid_remove()

        self._dismiss_button = ttk.Button(
            self,
            text="Dismiss",
            command=self.clear,
            takefocus=True,
            style="TButton",
        )
        self._dismiss_button.grid(row=0, column=1, padx=(0, padding[0]))

        self._current_severity: Severity = "info"
        self._visible = False
        self.hide()

    def apply_palette(self, palette: ThemePalette) -> None:
        """Update severity colour mapping from the active theme palette."""

        self._styles = {
            "info": StatusStyle(palette.banner_info_bg, palette.banner_info_text),
            "success": StatusStyle(
                palette.banner_success_bg, palette.banner_success_text
            ),
            "warning": StatusStyle(
                palette.banner_warning_bg, palette.banner_warning_text
            ),
            "error": StatusStyle(palette.banner_error_bg, palette.banner_error_text),
        }
        self._apply_style(self._current_severity)

    def show(
        self,
        message: str,
        *,
        severity: Severity = "info",
        detail: str | None = None,
    ) -> None:
        """Show a message with the provided severity."""

        self._current_severity = severity
        self._message_var.set(message)
        self._apply_style(severity)
        self._set_detail(detail)
        if not self._visible:
            self.grid()
            self._visible = True

    # Fix: ux_accessibility_status_guidance
    def show_error(self, message: str, *, detail: str | None = None) -> None:
        """Show an error message with actionable follow-up guidance."""

        guidance = (
            detail
            if detail and detail.strip()
            else (
                "Review the extraction log for more details or generate the JSON "
                "report for a full summary."
            )
        )
        self.show(message, severity="error", detail=guidance)

    def show_success(self, message: str, *, detail: str | None = None) -> None:
        self.show(message, severity="success", detail=detail)

    def show_warning(self, message: str, *, detail: str | None = None) -> None:
        self.show(message, severity="warning", detail=detail)

    def hide(self) -> None:
        """Hide the banner from view without clearing the current text."""

        self.grid_remove()
        self._visible = False

    def clear(self) -> None:
        """Reset the banner to the default ready state."""

        self._message_var.set("Ready")
        self._set_detail(None)
        self.show("Ready", severity="info")
        self.hide()

    def _apply_style(self, severity: Severity) -> None:
        style = self._styles.get(severity)
        if style is None:
            return
        self.configure(style="Main.TFrame")
        self._label.configure(style=self._style_name(severity))
        self._label.configure(background=style.background, foreground=style.foreground)
        self._detail_label.configure(background=style.background, foreground=style.foreground)
        self.configure(background=style.background)
        self._dismiss_button.configure(style="TButton")
        # Ensure ttk picks up manual background values for accessibility.
        self._label.configure(anchor=tk.W)
        self._detail_label.configure(anchor=tk.W)

    def _set_detail(self, detail: str | None) -> None:
        """Update the secondary guidance text block."""

        detail_text = detail.strip() if detail else ""
        self._detail_var.set(detail_text)
        if detail_text:
            self._detail_label.grid()
        else:
            self._detail_label.grid_remove()

    @staticmethod
    def _style_name(severity: Severity) -> str:
        return {
            "info": "Banner.Info.TLabel",
            "success": "Banner.Success.TLabel",
            "warning": "Banner.Warning.TLabel",
            "error": "Banner.Error.TLabel",
        }[severity]


__all__ = ["StatusBanner"]

