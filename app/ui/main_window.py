"""Main application window.

Phase 0 shell: a tab bar with the five placeholder tabs, a read-only log
console at the bottom, and disabled Run/Stop buttons. No command is wired up
yet — later phases fill the tabs and enable the buttons.
"""

from __future__ import annotations

import customtkinter as ctk

from app import config
from app.core.dependency_check import (
    check_dependencies,
    format_missing_message,
    missing_dependencies,
)


class MainWindow(ctk.CTk):
    """The top-level app window."""

    def __init__(self) -> None:
        super().__init__()

        self.title(config.APP_TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(config.MIN_WINDOW_WIDTH, config.MIN_WINDOW_HEIGHT)

        # Root grid: tabview grows, control bar + log console stay fixed height.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # tabview
        self.grid_rowconfigure(1, weight=0)  # control bar
        self.grid_rowconfigure(2, weight=0)  # log console

        self._build_tabview()
        self._build_control_bar()
        self._build_log_console()

        # Report dependency status into the log, and pop a warning if needed.
        self.after(200, self._run_dependency_check)

    # -- Layout ------------------------------------------------------------
    def _build_tabview(self) -> None:
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="nsew")
        for name in config.TAB_NAMES:
            self.tabview.add(name)
        # Content is added in later phases; tabs are intentionally empty now.
        self.tabview.set(config.TAB_NAMES[0])

    def _build_control_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, padx=12, pady=6, sticky="ew")

        # Run/Stop are disabled until Phase 1 wires a real command.
        self.run_button = ctk.CTkButton(bar, text="Run", width=100, state="disabled")
        self.run_button.pack(side="left")

        self.stop_button = ctk.CTkButton(
            bar, text="Stop", width=100, state="disabled"
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        self.status_label = ctk.CTkLabel(
            bar, text="Idle — no command wired yet (Phase 0 scaffold)."
        )
        self.status_label.pack(side="right")

    def _build_log_console(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, padx=12, pady=(6, 12), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(frame, text="Log", anchor="w")
        label.grid(row=0, column=0, padx=8, pady=(6, 0), sticky="w")

        self.log_console = ctk.CTkTextbox(frame, height=150, wrap="word")
        self.log_console.grid(row=1, column=0, padx=8, pady=(2, 8), sticky="ew")
        # Read-only placeholder for now.
        self.log_console.configure(state="disabled")

    # -- Log helpers -------------------------------------------------------
    def log(self, message: str) -> None:
        """Append a line to the read-only log console."""
        self.log_console.configure(state="normal")
        self.log_console.insert("end", message + "\n")
        self.log_console.see("end")
        self.log_console.configure(state="disabled")

    # -- Dependency check --------------------------------------------------
    def _run_dependency_check(self) -> None:
        for dep in check_dependencies():
            mark = "OK" if dep.found else "MISSING"
            self.log(f"[{mark}] {dep.name}: {dep.detail}")

        missing = missing_dependencies()
        if missing:
            self._show_dependency_warning(missing)

    def _show_dependency_warning(self, missing: list) -> None:
        body = format_missing_message(missing)

        dialog = ctk.CTkToplevel(self)
        dialog.title("Missing dependencies")
        dialog.geometry("560x420")
        dialog.transient(self)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ctk.CTkLabel(
            dialog,
            text="Some required tools were not found",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        header.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")

        text = ctk.CTkTextbox(dialog, wrap="word")
        text.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        text.insert("1.0", body)
        text.configure(state="disabled")

        close = ctk.CTkButton(dialog, text="Continue anyway", command=dialog.destroy)
        close.grid(row=2, column=0, padx=16, pady=(4, 16))

        # Make sure it lands in front of the main window.
        dialog.after(100, dialog.lift)


def launch() -> None:
    """Configure the theme and run the app main loop."""
    ctk.set_appearance_mode(config.APPEARANCE_MODE)
    ctk.set_default_color_theme(config.COLOR_THEME)
    app = MainWindow()
    app.mainloop()
