"""Core tab: URL, format selection, output template, and download path.

Builds the primary download controls and knows how to translate its inputs into
a yt-dlp argument list. It holds no subprocess logic — MainWindow owns the
runner and calls :meth:`build_download_args` / :meth:`get_url` when Run is hit.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app import config


def _default_download_dir() -> str:
    """User's Downloads folder if it exists, otherwise empty."""
    downloads = Path.home() / "Downloads"
    return str(downloads) if downloads.is_dir() else ""


class CoreTab:
    """Builds and owns the Core tab widgets inside a parent frame."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_state_change: Callable[[], None],
        on_list_formats: Callable[[], None],
    ) -> None:
        """Create the Core tab.

        Args:
            master: The tab frame to build into (from ``CTkTabview.tab(...)``).
            on_state_change: Called whenever inputs change so the window can
                re-evaluate whether Run should be enabled.
            on_list_formats: Called when the user clicks "List available
                formats". The window runs ``yt-dlp -F`` and shows the output.
        """
        self._master = master
        self._on_state_change = on_state_change
        self._on_list_formats = on_list_formats

        # Run-lock (False while a download runs) and format-active (False when the
        # Audio tab's extract-audio is on) together decide the format controls'
        # enabled state.
        self._unlocked = True
        self._format_active = True

        master.grid_columnconfigure(1, weight=1)
        row = 0

        # -- URL -----------------------------------------------------------
        ctk.CTkLabel(master, text="URL:").grid(
            row=row, column=0, padx=(12, 6), pady=(12, 6), sticky="w"
        )
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", lambda *_: self._on_state_change())
        self.url_entry = ctk.CTkEntry(
            master,
            textvariable=self.url_var,
            placeholder_text="https://... (video or playlist URL)",
        )
        self.url_entry.grid(
            row=row, column=1, columnspan=2, padx=(0, 12), pady=(12, 6), sticky="ew"
        )
        row += 1

        # -- Format --------------------------------------------------------
        ctk.CTkLabel(master, text="Format:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.format_menu = ctk.CTkOptionMenu(
            master,
            values=list(config.FORMAT_PRESETS.keys()),
            command=lambda _: self._on_format_change(),
        )
        self.format_menu.set(next(iter(config.FORMAT_PRESETS)))
        self.format_menu.grid(row=row, column=1, padx=(0, 6), pady=6, sticky="w")

        self.list_formats_button = ctk.CTkButton(
            master, text="List available formats", command=self._on_list_formats
        )
        self.list_formats_button.grid(row=row, column=2, padx=(0, 12), pady=6, sticky="e")
        row += 1

        # Inline note shown when the Audio tab's extract-audio suppresses -f.
        self.format_note = ctk.CTkLabel(
            master,
            text="Video format is set by the Audio tab (extract-audio is on).",
            text_color="gray",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._format_note_row = row
        row += 1

        # Custom format entry (hidden unless "Custom format string..." chosen).
        self.custom_format_var = ctk.StringVar()
        self.custom_format_var.trace_add("write", lambda *_: self._on_state_change())
        self.custom_format_entry = ctk.CTkEntry(
            master,
            textvariable=self.custom_format_var,
            placeholder_text="Raw -f value, e.g. bestvideo[ext=mp4]+bestaudio",
        )
        self._custom_format_row = row
        row += 1

        # -- Output template ----------------------------------------------
        ctk.CTkLabel(master, text="Output template:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.output_menu = ctk.CTkOptionMenu(
            master,
            values=list(config.OUTPUT_PRESETS.keys()),
            command=lambda _: self._on_output_change(),
        )
        self.output_menu.set(next(iter(config.OUTPUT_PRESETS)))
        self.output_menu.grid(
            row=row, column=1, columnspan=2, padx=(0, 12), pady=6, sticky="ew"
        )
        row += 1

        self.custom_output_var = ctk.StringVar()
        self.custom_output_var.trace_add("write", lambda *_: self._on_state_change())
        self.custom_output_entry = ctk.CTkEntry(
            master,
            textvariable=self.custom_output_var,
            placeholder_text="Custom -o template, e.g. %(id)s.%(ext)s",
        )
        self._custom_output_row = row
        row += 1

        # -- Download path -------------------------------------------------
        ctk.CTkLabel(master, text="Download folder:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.path_var = ctk.StringVar(value=_default_download_dir())
        self.path_entry = ctk.CTkEntry(
            master,
            textvariable=self.path_var,
            placeholder_text="Leave blank to use the current directory",
        )
        self.path_entry.grid(row=row, column=1, padx=(0, 6), pady=6, sticky="ew")
        self.browse_button = ctk.CTkButton(
            master, text="Browse...", width=90, command=self._browse
        )
        self.browse_button.grid(row=row, column=2, padx=(0, 12), pady=6, sticky="e")
        row += 1

    # -- Widget callbacks --------------------------------------------------
    def _on_format_change(self) -> None:
        if self.format_menu.get() == config.CUSTOM_FORMAT_LABEL:
            self.custom_format_entry.grid(
                row=self._custom_format_row,
                column=1,
                columnspan=2,
                padx=(0, 12),
                pady=(0, 6),
                sticky="ew",
            )
        else:
            self.custom_format_entry.grid_remove()
        self._on_state_change()

    def _on_output_change(self) -> None:
        if self.output_menu.get() == config.CUSTOM_OUTPUT_LABEL:
            self.custom_output_entry.grid(
                row=self._custom_output_row,
                column=1,
                columnspan=2,
                padx=(0, 12),
                pady=(0, 6),
                sticky="ew",
            )
        else:
            self.custom_output_entry.grid_remove()
        self._on_state_change()

    def _browse(self) -> None:
        initial = self.path_var.get() or str(Path.home())
        chosen = filedialog.askdirectory(initialdir=initial, title="Choose download folder")
        if chosen:
            self.path_var.set(chosen)

    # -- Public accessors --------------------------------------------------
    def get_url(self) -> str:
        """The trimmed URL text."""
        return self.url_var.get().strip()

    def get_download_dir(self) -> str:
        """The trimmed download-folder path (empty if unset)."""
        return self.path_var.get().strip()

    def is_valid(self) -> bool:
        """Run is allowed only when a non-empty URL is present."""
        return bool(self.get_url())

    # -- Preset state (UI values, distinct from get_args CLI flags) ---------
    def get_state(self) -> dict:
        """Serialize the tab's control values for a preset."""
        return {
            "url": self.url_var.get(),
            "format": self.format_menu.get(),
            "custom_format": self.custom_format_var.get(),
            "output": self.output_menu.get(),
            "custom_output": self.custom_output_var.get(),
            "path": self.path_var.get(),
        }

    def set_state(self, state: dict) -> None:
        """Restore control values from a preset, falling back per missing key."""
        self.url_var.set(state.get("url", ""))

        fmt = state.get("format", "")
        if fmt in config.FORMAT_PRESETS:
            self.format_menu.set(fmt)
        else:
            self.format_menu.set(next(iter(config.FORMAT_PRESETS)))
        self.custom_format_var.set(state.get("custom_format", ""))

        out = state.get("output", "")
        if out in config.OUTPUT_PRESETS:
            self.output_menu.set(out)
        else:
            self.output_menu.set(next(iter(config.OUTPUT_PRESETS)))
        self.custom_output_var.set(state.get("custom_output", ""))

        self.path_var.set(state.get("path", ""))

        # Reveal/hide the custom entries to match the restored dropdowns.
        self._on_format_change()
        self._on_output_change()

    def set_controls_enabled(self, enabled: bool) -> None:
        """Lock/unlock all inputs while a run is in progress."""
        self._unlocked = enabled
        self._refresh_states()

    def set_format_active(self, active: bool) -> None:
        """Grey out (or restore) the video-format controls.

        Called by the window when the Audio tab's extract-audio toggle flips.
        When inactive, the format controls are disabled, an inline note explains
        why, and :meth:`build_download_args` omits ``-f`` so no conflicting video
        format selector is sent alongside audio extraction.
        """
        self._format_active = active
        if active:
            self.format_note.grid_remove()
        else:
            self.format_note.grid(
                row=self._format_note_row,
                column=1,
                columnspan=2,
                padx=(0, 12),
                pady=(0, 4),
                sticky="w",
            )
        self._refresh_states()

    def _refresh_states(self) -> None:
        """Apply enabled/disabled state to every widget from the tracked flags."""
        base = "normal" if self._unlocked else "disabled"
        for widget in (
            self.url_entry,
            self.output_menu,
            self.path_entry,
            self.browse_button,
            self.custom_output_entry,
        ):
            widget.configure(state=base)

        fmt_state = "normal" if (self._unlocked and self._format_active) else "disabled"
        for widget in (
            self.format_menu,
            self.list_formats_button,
            self.custom_format_entry,
        ):
            widget.configure(state=fmt_state)

    def _selected_format(self) -> str:
        """The resolved -f value from either the preset or the custom entry."""
        label = self.format_menu.get()
        if label == config.CUSTOM_FORMAT_LABEL:
            return self.custom_format_var.get().strip()
        return config.FORMAT_PRESETS.get(label, "")

    def _selected_output(self) -> str:
        """The resolved -o template from either the preset or the custom entry."""
        label = self.output_menu.get()
        if label == config.CUSTOM_OUTPUT_LABEL:
            return self.custom_output_var.get().strip()
        return config.OUTPUT_PRESETS.get(label, "")

    def build_download_args(self) -> list[str]:
        """Translate the Core tab inputs into yt-dlp flags (URL not included)."""
        args: list[str] = []

        # Omit -f entirely when the Audio tab suppressed video format selection
        # (extract-audio on) so we don't send a conflicting video selector.
        fmt = self._selected_format()
        if fmt and self._format_active:
            args += ["-f", fmt]

        template = self._selected_output()
        if template:
            args += ["-o", template]

        path = self.path_var.get().strip()
        if path:
            args += ["-P", path]

        return args
