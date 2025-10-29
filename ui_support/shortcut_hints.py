"""Helpers for surfacing keyboard shortcut hints in the UI."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Iterable, Tuple


ShortcutHint = Tuple[tk.Widget, str]


# Fix: ux_accessibility_keyboard_hints
@dataclass
class ShortcutHintManager:
    """Attach hover/focus hints to buttons without custom tooltip widgets."""

    status_var: tk.StringVar

    def __post_init__(self) -> None:
        self._default_message: str = self.status_var.get() or "Ready"

    def set_default_message(self, message: str) -> None:
        """Update the default status text shown when hints are not active."""

        self._default_message = message or "Ready"
        if not self.status_var.get():
            self.status_var.set(self._default_message)

    def register_hints(self, hints: Iterable[ShortcutHint]) -> None:
        """Bind hover and focus events to surface shortcut hints."""

        for widget, message in hints:
            widget.bind(
                "<Enter>",
                lambda _event, msg=message: self.status_var.set(msg),
                add="+",
            )
            widget.bind(
                "<FocusIn>",
                lambda _event, msg=message: self.status_var.set(msg),
                add="+",
            )
            widget.bind(
                "<Leave>",
                lambda _event: self.status_var.set(self._default_message),
                add="+",
            )
            widget.bind(
                "<FocusOut>",
                lambda _event: self.status_var.set(self._default_message),
                add="+",
            )


__all__ = ["ShortcutHintManager", "ShortcutHint"]
