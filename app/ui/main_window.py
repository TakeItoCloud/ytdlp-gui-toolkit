"""Main application window.

Hosts the tabbed sections (only Core is functional this phase), a parsed
progress bar with a status label, Run/Stop controls, and a collapsible raw-log
panel for full yt-dlp output.

Threading note: the subprocess runner invokes its callbacks from a worker
thread. Those callbacks only push events onto a thread-safe queue; all widget
updates happen on the main thread via a periodic ``after()`` poll of that queue.
"""

from __future__ import annotations

import queue

import customtkinter as ctk

from app import config
from app.core.dependency_check import (
    check_dependencies,
    format_missing_message,
    missing_dependencies,
)
from app.core.runner import CommandRunner
from app.ui.tabs.audio_tab import AudioTab
from app.ui.tabs.core_tab import CoreTab
from app.ui.tabs.playlist_tab import PlaylistTab

_STATUS_MAX = 90  # truncate long status lines so the label doesn't blow out


class MainWindow(ctk.CTk):
    """The top-level app window."""

    def __init__(self) -> None:
        super().__init__()

        self.title(config.APP_TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.minsize(config.MIN_WINDOW_WIDTH, config.MIN_WINDOW_HEIGHT)

        self.runner = CommandRunner()
        self._events: queue.Queue[tuple] = queue.Queue()
        self._mode: str = ""  # "download" or "list"
        self._stopping = False
        self._raw_log_visible = False

        # Root grid: tabview grows; progress, controls, and log are fixed.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # tabview
        self.grid_rowconfigure(1, weight=0)  # progress row
        self.grid_rowconfigure(2, weight=0)  # control bar
        self.grid_rowconfigure(3, weight=0)  # raw log (collapsible)

        self._build_tabview()
        self._build_progress_row()
        self._build_control_bar()
        self._build_log_console()

        self._update_run_state()

        # Poll the event queue on the main loop, and run the startup dep check.
        self.after(100, self._drain_events)
        self.after(200, self._run_dependency_check)

    # -- Layout ------------------------------------------------------------
    def _build_tabview(self) -> None:
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="nsew")
        for name in config.TAB_NAMES:
            self.tabview.add(name)

        # Core and Audio tabs are functional; the rest stay empty until later.
        self.core_tab = CoreTab(
            self.tabview.tab("Core"),
            on_state_change=self._update_run_state,
            on_list_formats=self._on_list_formats,
        )
        self.audio_tab = AudioTab(
            self.tabview.tab("Audio"),
            on_extract_change=self._on_audio_extract_change,
        )
        self.playlist_tab = PlaylistTab(
            self.tabview.tab("Playlist"),
            get_download_dir=self.core_tab.get_download_dir,
        )
        self.tabview.set("Core")

    def _on_audio_extract_change(self) -> None:
        """Grey/restore the Core tab's video-format controls to match audio mode."""
        self.core_tab.set_format_active(not self.audio_tab.is_extract_on())

    def _build_progress_row(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.grid(row=0, column=0, padx=(0, 12), pady=4, sticky="ew")
        self.progress_bar.set(0.0)

        self.status_label = ctk.CTkLabel(frame, text="Idle", anchor="w")
        self.status_label.grid(row=1, column=0, padx=0, pady=(0, 2), sticky="w")

    def _build_control_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=2, column=0, padx=12, pady=4, sticky="ew")

        self.run_button = ctk.CTkButton(
            bar, text="Run", width=100, command=self._on_run
        )
        self.run_button.pack(side="left")

        self.stop_button = ctk.CTkButton(
            bar, text="Stop", width=100, state="disabled", command=self._on_stop
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        self.toggle_log_button = ctk.CTkButton(
            bar, text="Show raw log ▸", width=130, command=self._toggle_raw_log
        )
        self.toggle_log_button.pack(side="right")

    def _build_log_console(self) -> None:
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        label = ctk.CTkLabel(self.log_frame, text="Raw log", anchor="w")
        label.grid(row=0, column=0, padx=8, pady=(6, 0), sticky="w")

        self.log_console = ctk.CTkTextbox(self.log_frame, height=180, wrap="word")
        self.log_console.grid(row=1, column=0, padx=8, pady=(2, 8), sticky="nsew")
        self.log_console.configure(state="disabled")

        # Collapsed by default; _toggle_raw_log grids it in.

    # -- Raw log collapse/expand ------------------------------------------
    def _toggle_raw_log(self, *, show: bool | None = None) -> None:
        target = (not self._raw_log_visible) if show is None else show
        if target == self._raw_log_visible:
            return
        self._raw_log_visible = target
        if target:
            self.grid_rowconfigure(3, weight=1)
            self.log_frame.grid(row=3, column=0, padx=12, pady=(4, 12), sticky="nsew")
            self.toggle_log_button.configure(text="Hide raw log ▾")
        else:
            self.log_frame.grid_remove()
            self.grid_rowconfigure(3, weight=0)
            self.toggle_log_button.configure(text="Show raw log ▸")

    # -- Log helpers -------------------------------------------------------
    def log(self, message: str) -> None:
        """Append a line to the read-only raw-log panel."""
        self.log_console.configure(state="normal")
        self.log_console.insert("end", message + "\n")
        self.log_console.see("end")
        self.log_console.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        if len(text) > _STATUS_MAX:
            text = text[: _STATUS_MAX - 1] + "…"
        self.status_label.configure(text=text)

    # -- Run-state management ---------------------------------------------
    def _update_run_state(self) -> None:
        """Enable Run only when idle and the Core tab has a valid URL."""
        running = self.runner.is_running()
        can_run = (not running) and self.core_tab.is_valid()
        self.run_button.configure(state="normal" if can_run else "disabled")
        self.stop_button.configure(state="normal" if running else "disabled")

    # -- Run / Stop / List formats ----------------------------------------
    def _on_run(self) -> None:
        url = self.core_tab.get_url()
        if not url:
            self._set_status("Enter a URL first.")
            return
        args = [
            *self.core_tab.build_download_args(),
            *self.audio_tab.get_args(),
            *self.playlist_tab.get_args(),
            url,
        ]
        self._launch(args, mode="download", running_status="Starting download…")

    def _on_list_formats(self) -> None:
        if self.runner.is_running():
            self._set_status("A run is already in progress.")
            return
        url = self.core_tab.get_url()
        if not url:
            self._set_status("Enter a URL before listing formats.")
            self.log("[info] List formats requires a URL.")
            return
        # Show the raw log so the -F table is visible.
        self._toggle_raw_log(show=True)
        self._launch(["-F", url], mode="list", running_status="Listing formats…")

    def _launch(self, args: list[str], *, mode: str, running_status: str) -> None:
        self._mode = mode
        self._stopping = False

        self.progress_bar.set(0.0)
        self._set_status(running_status)
        self.log(f"$ yt-dlp {' '.join(args)}")

        # Lock the UI for the duration of the run.
        self.core_tab.set_controls_enabled(False)
        self.audio_tab.set_controls_enabled(False)
        self.playlist_tab.set_controls_enabled(False)
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        self.runner.run(
            args,
            on_output=lambda line: self._events.put(("output", line)),
            on_progress=lambda pct, line: self._events.put(("progress", pct, line)),
            on_done=lambda rc: self._events.put(("done", rc)),
        )

    def _on_stop(self) -> None:
        self._stopping = True
        self._set_status("Stopping…")
        self.runner.stop()

    # -- Event queue (worker thread -> main thread) -----------------------
    def _drain_events(self) -> None:
        try:
            while True:
                event = self._events.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _handle_event(self, event: tuple) -> None:
        kind = event[0]
        if kind == "output":
            self.log(event[1])
        elif kind == "progress":
            pct, line = event[1], event[2]
            if pct is not None:
                self.progress_bar.set(pct / 100.0)
                if self._mode == "download":
                    self._set_status(f"Downloading… {pct:.1f}%")
            else:
                # Non-progress status line (merge, postprocess, playlist header…).
                self._set_status(line)
        elif kind == "done":
            self._on_done(event[1])

    def _on_done(self, returncode: int) -> None:
        self.core_tab.set_controls_enabled(True)
        self.audio_tab.set_controls_enabled(True)
        self.playlist_tab.set_controls_enabled(True)

        if self._stopping:
            self._set_status("Stopped.")
        elif returncode == 0:
            if self._mode == "download":
                self.progress_bar.set(1.0)
                self._set_status("Completed successfully.")
            else:
                self._set_status("Formats listed (see raw log).")
        else:
            self._set_status(f"Failed (exit code {returncode}). See raw log.")

        self._mode = ""
        self._update_run_state()

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

        dialog.after(100, dialog.lift)


def launch() -> None:
    """Configure the theme and run the app main loop."""
    ctk.set_appearance_mode(config.APPEARANCE_MODE)
    ctk.set_default_color_theme(config.COLOR_THEME)
    app = MainWindow()
    app.mainloop()
