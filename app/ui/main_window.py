"""Main application window.

Hosts the five tabbed sections, a live command-preview panel with a copy button,
a parsed progress bar with a status label, Run/Stop controls, preset save/load,
a yt-dlp self-update button, and a collapsible raw-log panel for full output.

Threading note: the subprocess runner invokes its callbacks from a worker
thread. Those callbacks only push events onto a thread-safe queue; all widget
updates happen on the main thread via a periodic ``after()`` poll of that queue.
"""

from __future__ import annotations

import json
import queue
import shlex
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app import config
from app.core.dependency_check import (
    check_dependencies,
    format_missing_message,
    missing_dependencies,
)
from app.core.runner import CommandRunner
from app.ui.tabs.advanced_tab import AdvancedTab
from app.ui.tabs.audio_tab import AudioTab
from app.ui.tabs.core_tab import CoreTab
from app.ui.tabs.playlist_tab import PlaylistTab
from app.ui.tabs.subtitles_tab import SubtitlesTab

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
        self._mode: str = ""  # "download", "list", or "update"
        self._stopping = False
        self._raw_log_visible = False
        self._preview_last = ""

        # Root grid: tabview grows; preview, progress, controls, and log fixed.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)  # tabview
        self.grid_rowconfigure(1, weight=0)  # command preview
        self.grid_rowconfigure(2, weight=0)  # progress row
        self.grid_rowconfigure(3, weight=0)  # control bar
        self.grid_rowconfigure(4, weight=0)  # raw log (collapsible)

        self._build_tabview()
        self._build_preview_row()
        self._build_progress_row()
        self._build_control_bar()
        self._build_log_console()

        self._update_run_state()

        # Poll the event queue and refresh the live preview on the main loop,
        # and run the startup dependency check.
        self.after(100, self._drain_events)
        self.after(200, self._run_dependency_check)
        self.after(300, self._refresh_preview)

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
        self.subtitles_tab = SubtitlesTab(
            self.tabview.tab("Subtitles"),
            is_extract_audio_on=self.audio_tab.is_extract_on,
        )
        self.advanced_tab = AdvancedTab(self.tabview.tab("Advanced"))
        self.tabview.set("Core")

    def _on_audio_extract_change(self) -> None:
        """Sync controls that depend on the Audio tab's extract-audio mode."""
        extract_on = self.audio_tab.is_extract_on()
        self.core_tab.set_format_active(not extract_on)
        self.subtitles_tab.refresh_audio_dependency()

    def _build_preview_row(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Command preview", anchor="w").grid(
            row=0, column=0, padx=8, pady=(6, 0), sticky="w"
        )

        # Read-only, wraps so long commands stay fully visible.
        self.preview_box = ctk.CTkTextbox(frame, height=54, wrap="word")
        self.preview_box.grid(row=1, column=0, padx=(8, 6), pady=(2, 8), sticky="ew")
        self.preview_box.configure(state="disabled")

        self.copy_button = ctk.CTkButton(
            frame, text="Copy", width=90, command=self._on_copy_command
        )
        self.copy_button.grid(row=1, column=1, padx=(0, 8), pady=(2, 8), sticky="n")

    def _build_progress_row(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.grid(row=0, column=0, padx=(0, 12), pady=4, sticky="ew")
        self.progress_bar.set(0.0)

        self.status_label = ctk.CTkLabel(frame, text="Idle", anchor="w")
        self.status_label.grid(row=1, column=0, padx=0, pady=(0, 2), sticky="w")

    def _build_control_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, padx=12, pady=4, sticky="ew")

        self.run_button = ctk.CTkButton(
            bar, text="Run", width=100, command=self._on_run
        )
        self.run_button.pack(side="left")

        self.stop_button = ctk.CTkButton(
            bar, text="Stop", width=100, state="disabled", command=self._on_stop
        )
        self.stop_button.pack(side="left", padx=(8, 0))

        # Right side (packed right-to-left): raw-log toggle, then utilities.
        self.toggle_log_button = ctk.CTkButton(
            bar, text="Show raw log ▸", width=130, command=self._toggle_raw_log
        )
        self.toggle_log_button.pack(side="right")

        self.update_button = ctk.CTkButton(
            bar, text="Update yt-dlp", width=120, command=self._on_update_ytdlp
        )
        self.update_button.pack(side="right", padx=(0, 8))

        self.load_button = ctk.CTkButton(
            bar, text="Load preset", width=110, command=self._on_load_preset
        )
        self.load_button.pack(side="right", padx=(0, 8))

        self.save_button = ctk.CTkButton(
            bar, text="Save preset", width=110, command=self._on_save_preset
        )
        self.save_button.pack(side="right", padx=(0, 8))

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
            self.grid_rowconfigure(4, weight=1)
            self.log_frame.grid(row=4, column=0, padx=12, pady=(4, 12), sticky="nsew")
            self.toggle_log_button.configure(text="Hide raw log ▾")
        else:
            self.log_frame.grid_remove()
            self.grid_rowconfigure(4, weight=0)
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

    # -- Shared args / preview --------------------------------------------
    def _collect_flag_args(self) -> list[str]:
        """Concatenate every tab's yt-dlp flags (URL not included).

        Single source of truth for both the Run handler and the live preview so
        the previewed command is exactly what Run would execute.
        """
        return [
            *self.core_tab.build_download_args(),
            *self.audio_tab.get_args(),
            *self.playlist_tab.get_args(),
            *self.subtitles_tab.get_args(),
            *self.advanced_tab.get_args(),
        ]

    def _preview_command_string(self) -> str:
        """The full yt-dlp command as it would run (URL, or <URL> if empty)."""
        url = self.core_tab.get_url() or "<URL>"
        parts = ["yt-dlp", *self._collect_flag_args(), url]
        return shlex.join(parts)

    def _refresh_preview(self) -> None:
        command = self._preview_command_string()
        if command != self._preview_last:
            self._preview_last = command
            self.preview_box.configure(state="normal")
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", command)
            self.preview_box.configure(state="disabled")
        self.after(400, self._refresh_preview)

    def _on_copy_command(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._preview_command_string())
        self.copy_button.configure(text="Copied!")
        self.after(1000, lambda: self.copy_button.configure(text="Copy"))

    # -- Run / Stop / List formats ----------------------------------------
    def _on_run(self) -> None:
        url = self.core_tab.get_url()
        if not url:
            self._set_status("Enter a URL first.")
            return
        args = [*self._collect_flag_args(), url]
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
        self.subtitles_tab.set_controls_enabled(False)
        self.advanced_tab.set_controls_enabled(False)
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._set_utility_enabled(False)

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

    # -- yt-dlp self-update ------------------------------------------------
    def _on_update_ytdlp(self) -> None:
        """Run ``yt-dlp -U`` via the shared runner; no URL required."""
        if self.runner.is_running():
            self._set_status("A run is already in progress.")
            return
        self._toggle_raw_log(show=True)
        self._launch(["-U"], mode="update", running_status="Updating yt-dlp…")

    # -- Presets (full UI state, save/load JSON) --------------------------
    def _presets_dir(self) -> Path:
        """The app's presets/ folder (created on first use)."""
        directory = Path(__file__).resolve().parents[2] / "presets"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _collect_state(self) -> dict:
        """Serialize every tab's UI values into a preset dict."""
        return {
            "version": 1,
            "core": self.core_tab.get_state(),
            "audio": self.audio_tab.get_state(),
            "playlist": self.playlist_tab.get_state(),
            "subtitles": self.subtitles_tab.get_state(),
            "advanced": self.advanced_tab.get_state(),
        }

    def _apply_state(self, state: dict) -> None:
        """Restore every tab from a preset dict, then resync cross-tab deps."""
        self.core_tab.set_state(state.get("core", {}))
        self.audio_tab.set_state(state.get("audio", {}))
        self.playlist_tab.set_state(state.get("playlist", {}))
        self.subtitles_tab.set_state(state.get("subtitles", {}))
        self.advanced_tab.set_state(state.get("advanced", {}))
        # One resync so audio-dependent controls (Core format, embed-subs) match.
        self._on_audio_extract_change()
        self._update_run_state()

    def _on_save_preset(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save preset",
            initialdir=str(self._presets_dir()),
            defaultextension=".json",
            filetypes=[("JSON presets", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(self._collect_state(), handle, indent=2)
        except OSError as exc:
            self._set_status(f"Could not save preset: {exc}")
            self.log(f"[error] save preset: {exc}")
            return
        self._set_status(f"Preset saved: {Path(path).name}")

    def _on_load_preset(self) -> None:
        path = filedialog.askopenfilename(
            title="Load preset",
            initialdir=str(self._presets_dir()),
            filetypes=[("JSON presets", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as handle:
                state = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            self._set_status(f"Could not load preset: {exc}")
            self.log(f"[error] load preset: {exc}")
            return
        if not isinstance(state, dict):
            self._set_status("Preset file is not a valid preset.")
            self.log("[error] load preset: top-level JSON is not an object.")
            return
        # set_state on each tab already falls back per missing/unknown key.
        self._apply_state(state)
        self._set_status(f"Preset loaded: {Path(path).name}")

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
        self.subtitles_tab.set_controls_enabled(True)
        self.advanced_tab.set_controls_enabled(True)
        self._set_utility_enabled(True)

        if self._stopping:
            self._set_status("Stopped.")
        elif returncode == 0:
            if self._mode == "download":
                self.progress_bar.set(1.0)
                self._set_status("Completed successfully.")
            elif self._mode == "update":
                self._set_status("yt-dlp update finished (see raw log).")
            else:
                self._set_status("Formats listed (see raw log).")
        else:
            self._set_status(f"Failed (exit code {returncode}). See raw log.")

        self._mode = ""
        self._update_run_state()

    def _set_utility_enabled(self, enabled: bool) -> None:
        """Enable/disable the preset + update buttons during a run."""
        state = "normal" if enabled else "disabled"
        for button in (self.save_button, self.load_button, self.update_button):
            button.configure(state=state)

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
