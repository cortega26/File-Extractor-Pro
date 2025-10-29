"""Keyboard shortcut and focus management helpers for the Tkinter UI."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Shortcut:
    """Represent a keyboard shortcut binding."""

    sequence: str
    handler: Callable[[tk.Event], str]


# Fix: Q-103
class KeyboardManager:
    """Manage keyboard accelerators and focus order for the GUI."""

    def __init__(self, master: tk.Misc) -> None:
        self._master = master
        self._registered_shortcuts: list[Shortcut] = []

    def register_shortcuts(
        self,
        shortcuts: dict[str, Callable[[tk.Event], str]],
    ) -> None:
        """Bind accelerator sequences to the provided handlers."""

        for sequence, handler in shortcuts.items():
            self._master.bind_all(sequence, handler, add="+")
            self._registered_shortcuts.append(Shortcut(sequence, handler))

    # Fix: Q-107
    def configure_focus_ring(
        self,
        *,
        preferred_order: Sequence[tk.Widget],
        skip: Sequence[tk.Widget] = (),
    ) -> None:
        """Ensure focus order emphasises actionable controls."""

        seen: set[int] = set()
        for widget in preferred_order:
            try:
                widget.configure(takefocus=True)  # type: ignore[call-arg]
                seen.add(id(widget))
            except tk.TclError:
                continue

        for widget in skip:
            if id(widget) in seen:
                continue
            try:
                widget.configure(takefocus=False)  # type: ignore[call-arg]
            except tk.TclError:
                continue

        if preferred_order:
            preferred_order[0].focus_set()

    def clear(self) -> None:
        """Remove registered shortcuts when tearing down the UI."""

        for shortcut in self._registered_shortcuts:
            self._master.unbind_all(shortcut.sequence)
        self._registered_shortcuts.clear()


__all__ = ["KeyboardManager"]
