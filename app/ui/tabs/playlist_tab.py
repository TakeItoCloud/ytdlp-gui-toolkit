"""Playlist tab: playlist handling, item ranges, and download archive.

Follows the per-tab pattern from Phases 1-2: the tab owns its widgets and
exposes :meth:`get_args` returning the yt-dlp flags for its state. MainWindow
concatenates each tab's args when Run is hit.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from app import config

# Deliberately loose: yt-dlp's --playlist-items grammar (ranges, steps, negative
# indices, comma mixes like "1,3,5-10,-5::2") is complex, so we only reject
# characters that can never be part of it rather than parsing the full syntax.
_ITEMS_ALLOWED_RE = re.compile(r"^[0-9,:\-\s]*$")


class PlaylistTab:
    """Builds and owns the Playlist tab widgets inside a parent frame."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        get_download_dir: Callable[[], str],
    ) -> None:
        """Create the Playlist tab.

        Args:
            master: The tab frame to build into (from ``CTkTabview.tab(...)``).
            get_download_dir: Returns the Core tab's current download folder, used
                to suggest a default archive path and seed the Browse dialog.
        """
        self._master = master
        self._get_download_dir = get_download_dir
        self._unlocked = True

        master.grid_columnconfigure(1, weight=1)
        row = 0

        # -- Playlist handling --------------------------------------------
        ctk.CTkLabel(master, text="Playlist handling:").grid(
            row=row, column=0, padx=(12, 6), pady=(14, 6), sticky="w"
        )
        self.handling_menu = ctk.CTkOptionMenu(
            master,
            values=list(config.PLAYLIST_HANDLING.keys()),
            command=lambda _: self._on_handling_change(),
        )
        self.handling_menu.set(next(iter(config.PLAYLIST_HANDLING)))
        self.handling_menu.grid(
            row=row, column=1, columnspan=2, padx=(0, 12), pady=(14, 6), sticky="w"
        )
        row += 1

        # -- Playlist items -----------------------------------------------
        ctk.CTkLabel(master, text="Playlist items:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.items_var = ctk.StringVar()
        self.items_var.trace_add("write", lambda *_: self._validate_items())
        self.items_entry = ctk.CTkEntry(
            master,
            textvariable=self.items_var,
            placeholder_text="e.g. 1,3,5-10  (blank = all items)",
        )
        self.items_entry.grid(
            row=row, column=1, columnspan=2, padx=(0, 12), pady=6, sticky="ew"
        )
        row += 1

        self.items_warning = ctk.CTkLabel(
            master,
            text="",
            text_color="#e06c50",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._items_warning_row = row
        row += 1

        # -- Download archive ---------------------------------------------
        self.archive_var = ctk.BooleanVar(value=False)
        self.archive_switch = ctk.CTkSwitch(
            master,
            text="Use download archive  (--download-archive)",
            variable=self.archive_var,
            command=self._on_archive_toggle,
        )
        self.archive_switch.grid(
            row=row, column=0, columnspan=3, padx=12, pady=(12, 4), sticky="w"
        )
        row += 1

        ctk.CTkLabel(master, text="Archive file:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.archive_path_var = ctk.StringVar()
        self.archive_entry = ctk.CTkEntry(
            master,
            textvariable=self.archive_path_var,
            placeholder_text="Path to a .txt archive of already-downloaded IDs",
        )
        self.archive_entry.grid(row=row, column=1, padx=(0, 6), pady=6, sticky="ew")
        self.archive_browse = ctk.CTkButton(
            master, text="Browse...", width=90, command=self._browse_archive
        )
        self.archive_browse.grid(row=row, column=2, padx=(0, 12), pady=6, sticky="e")
        row += 1

        # -- Inline help ---------------------------------------------------
        self.hint_label = ctk.CTkLabel(
            master,
            text=(
                "The archive records downloaded video IDs so re-runs skip them "
                "(works for video and audio-only)."
            ),
            text_color="gray",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self.hint_label.grid(
            row=row, column=0, columnspan=3, padx=12, pady=(8, 6), sticky="w"
        )

        self._refresh_states()

    # -- Widget callbacks --------------------------------------------------
    def _on_handling_change(self) -> None:
        self._refresh_states()

    def _on_archive_toggle(self) -> None:
        # On first enable with an empty path, suggest <download dir>/archive.txt.
        if self.archive_var.get() and not self.archive_path_var.get().strip():
            self.archive_path_var.set(self._default_archive_path())
        self._refresh_states()

    def _default_archive_path(self) -> str:
        base = self._get_download_dir()
        directory = Path(base) if base else Path.cwd()
        return str(directory / config.DEFAULT_ARCHIVE_FILENAME)

    def _browse_archive(self) -> None:
        current = self.archive_path_var.get().strip()
        if current:
            initial_dir = str(Path(current).parent)
            initial_file = Path(current).name
        else:
            base = self._get_download_dir()
            initial_dir = base if base else str(Path.cwd())
            initial_file = config.DEFAULT_ARCHIVE_FILENAME
        # asksaveasfilename lets the user pick an existing file OR name a new one.
        chosen = filedialog.asksaveasfilename(
            title="Select or create download-archive file",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".txt",
            confirmoverwrite=False,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if chosen:
            self.archive_path_var.set(chosen)

    # -- Validation --------------------------------------------------------
    def _validate_items(self) -> None:
        value = self.items_var.get()
        if value and not _ITEMS_ALLOWED_RE.match(value):
            self.items_warning.configure(
                text="Only digits, commas, colons and hyphens are allowed "
                "(e.g. 1,3,5-10)."
            )
            self.items_warning.grid(
                row=self._items_warning_row,
                column=1,
                columnspan=2,
                padx=(0, 12),
                pady=(0, 4),
                sticky="w",
            )
        else:
            self.items_warning.configure(text="")
            self.items_warning.grid_remove()

    # -- State management --------------------------------------------------
    def _refresh_states(self) -> None:
        """Apply enabled/disabled state to every widget from the tracked flags."""
        base = "normal" if self._unlocked else "disabled"
        self.handling_menu.configure(state=base)
        self.archive_switch.configure(state=base)

        # Playlist items is irrelevant when ignoring the playlist entirely.
        items_state = (
            "normal" if (self._unlocked and not self._is_no_playlist()) else "disabled"
        )
        self.items_entry.configure(state=items_state)

        archive_state = (
            "normal" if (self._unlocked and self.archive_var.get()) else "disabled"
        )
        self.archive_entry.configure(state=archive_state)
        self.archive_browse.configure(state=archive_state)

    def set_controls_enabled(self, enabled: bool) -> None:
        """Lock/unlock the tab while a run is in progress."""
        self._unlocked = enabled
        self._refresh_states()

    # -- Preset state (UI values, distinct from get_args CLI flags) ---------
    def get_state(self) -> dict:
        """Serialize the tab's control values for a preset."""
        return {
            "handling": self.handling_menu.get(),
            "items": self.items_var.get(),
            "archive_on": bool(self.archive_var.get()),
            "archive_path": self.archive_path_var.get(),
        }

    def set_state(self, state: dict) -> None:
        """Restore control values from a preset, falling back per missing key."""
        handling = state.get("handling", "")
        if handling in config.PLAYLIST_HANDLING:
            self.handling_menu.set(handling)
        else:
            self.handling_menu.set(next(iter(config.PLAYLIST_HANDLING)))

        self.items_var.set(state.get("items", ""))
        self.archive_var.set(bool(state.get("archive_on", False)))
        self.archive_path_var.set(state.get("archive_path", ""))

        self._refresh_states()
        self._validate_items()

    # -- Helpers / accessors ----------------------------------------------
    def _is_no_playlist(self) -> bool:
        return self.handling_menu.get() == config.PLAYLIST_NO_PLAYLIST_LABEL

    def get_args(self) -> list[str]:
        """The yt-dlp flags for the Playlist tab."""
        args: list[str] = []

        flag = config.PLAYLIST_HANDLING.get(self.handling_menu.get(), "")
        if flag:
            args.append(flag)

        # Item ranges only make sense when we aren't ignoring the playlist.
        items = self.items_var.get().strip()
        if items and not self._is_no_playlist():
            args += ["-I", items]

        if self.archive_var.get():
            archive_path = self.archive_path_var.get().strip()
            if archive_path:
                args += ["--download-archive", archive_path]

        return args
