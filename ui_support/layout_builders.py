"""UI layout builders extracted from the main Tkinter GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


# Fix: Q-103
def build_menu_bar(
    master: tk.Misc,
    *,
    on_exit: Callable[[], None],
    on_toggle_theme: Callable[[], None],
) -> tk.Menu:
    """Create the application menu bar with bound callbacks."""

    menu_bar = tk.Menu(master)
    master.config(menu=menu_bar)

    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="Exit", command=on_exit)
    menu_bar.add_cascade(label="File", menu=file_menu)

    options_menu = tk.Menu(menu_bar, tearoff=0)
    options_menu.add_command(label="Toggle Theme", command=on_toggle_theme)
    menu_bar.add_cascade(label="Options", menu=options_menu)

    return menu_bar


# Fix: Q-103
def build_status_bar(
    master: tk.Misc,
    *,
    status_var: tk.StringVar | None = None,
    row: int = 1,
) -> tuple[tk.StringVar, ttk.Label]:
    """Create a styled status bar bound to the provided variable."""

    status_variable = status_var or tk.StringVar()
    status_bar = ttk.Label(
        master,
        textvariable=status_variable,
        relief=tk.SUNKEN,
        anchor=tk.W,
        style="Status.TLabel",
    )
    status_bar.grid(row=row, column=0, sticky=tk.W + tk.E)
    return status_variable, status_bar


__all__ = ["build_menu_bar", "build_status_bar"]

