"""Subtitles tab: write subs / auto-subs, languages, and embedding.

Follows the per-tab pattern from Phases 1-3: the tab owns its widgets and
exposes :meth:`get_args` returning the yt-dlp flags for its state. MainWindow
concatenates each tab's args when Run is hit.

Cross-tab dependency: ``--embed-subs`` needs a video container to embed into, so
it is greyed out (and dropped from the command) when the Audio tab's
extract-audio-only mode is on. The tab reads that state through the
``is_extract_audio_on`` callable passed in, mirroring how the Playlist tab reads
``CoreTab.get_download_dir``; MainWindow calls :meth:`refresh_audio_dependency`
whenever the Audio toggle flips.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import customtkinter as ctk

# Deliberately loose (same philosophy as the playlist-items field): yt-dlp's
# --sub-langs accepts comma-separated codes, "all", exclusions like
# "all,-live_chat", and regex such as "en.*". We only reject characters that
# could never appear rather than parsing the grammar.
_LANGS_ALLOWED_RE = re.compile(r"^[A-Za-z0-9,.\-*_|()\[\]^$+?\s]*$")


class SubtitlesTab:
    """Builds and owns the Subtitles tab widgets inside a parent frame."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        is_extract_audio_on: Callable[[], bool],
    ) -> None:
        """Create the Subtitles tab.

        Args:
            master: The tab frame to build into (from ``CTkTabview.tab(...)``).
            is_extract_audio_on: Returns whether the Audio tab's extract-audio
                mode is active, used to grey out the embed-subs toggle.
        """
        self._master = master
        self._is_extract_audio_on = is_extract_audio_on
        self._unlocked = True

        master.grid_columnconfigure(1, weight=1)
        row = 0

        # -- Write subtitles ----------------------------------------------
        self.write_subs_var = ctk.BooleanVar(value=False)
        self.write_subs_switch = ctk.CTkSwitch(
            master,
            text="Write subtitles  (--write-subs)",
            variable=self.write_subs_var,
            command=self._on_write_toggle,
        )
        self.write_subs_switch.grid(
            row=row, column=0, columnspan=3, padx=12, pady=(14, 4), sticky="w"
        )
        row += 1

        # -- Write auto-generated subtitles -------------------------------
        self.write_auto_var = ctk.BooleanVar(value=False)
        self.write_auto_switch = ctk.CTkSwitch(
            master,
            text="Write auto-generated subtitles  (--write-auto-subs)",
            variable=self.write_auto_var,
            command=self._on_write_toggle,
        )
        self.write_auto_switch.grid(
            row=row, column=0, columnspan=3, padx=12, pady=4, sticky="w"
        )
        row += 1

        # -- Subtitle languages -------------------------------------------
        ctk.CTkLabel(master, text="Subtitle languages:").grid(
            row=row, column=0, padx=(12, 6), pady=(8, 6), sticky="w"
        )
        self.langs_var = ctk.StringVar()
        self.langs_var.trace_add("write", lambda *_: self._validate_langs())
        self.langs_entry = ctk.CTkEntry(
            master,
            textvariable=self.langs_var,
            placeholder_text="e.g. en,ja or all",
        )
        self.langs_entry.grid(
            row=row, column=1, columnspan=2, padx=(0, 12), pady=(8, 6), sticky="ew"
        )
        row += 1

        self.langs_warning = ctk.CTkLabel(
            master,
            text="",
            text_color="#e06c50",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._langs_warning_row = row
        row += 1

        # -- Embed subtitles ----------------------------------------------
        self.embed_var = ctk.BooleanVar(value=False)
        self.embed_switch = ctk.CTkSwitch(
            master,
            text="Embed subtitles into video  (--embed-subs)",
            variable=self.embed_var,
        )
        self.embed_switch.grid(
            row=row, column=0, columnspan=3, padx=12, pady=(8, 2), sticky="w"
        )
        row += 1

        # Inline note shown when extract-audio conflicts with embedding.
        self.embed_note = ctk.CTkLabel(
            master,
            text="Disabled: no video to embed into (extract-audio is on).",
            text_color="gray",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._embed_note_row = row
        row += 1

        # -- Inline help ---------------------------------------------------
        self.hint_label = ctk.CTkLabel(
            master,
            text=(
                "Turn on a write-subtitles switch to fetch subtitles; embedding "
                "works for mp4/webm/mkv."
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
    def _on_write_toggle(self) -> None:
        self._refresh_states()

    def refresh_audio_dependency(self) -> None:
        """Re-evaluate the embed-subs control after the Audio toggle changes."""
        self._refresh_states()

    # -- Validation --------------------------------------------------------
    def _validate_langs(self) -> None:
        value = self.langs_var.get()
        if value and not _LANGS_ALLOWED_RE.match(value):
            self.langs_warning.configure(
                text="Only language codes / regex are allowed "
                "(e.g. en,ja or all)."
            )
            self.langs_warning.grid(
                row=self._langs_warning_row,
                column=1,
                columnspan=2,
                padx=(0, 12),
                pady=(0, 4),
                sticky="w",
            )
        else:
            self.langs_warning.configure(text="")
            self.langs_warning.grid_remove()

    # -- State management --------------------------------------------------
    def _any_write_on(self) -> bool:
        return bool(self.write_subs_var.get() or self.write_auto_var.get())

    def _refresh_states(self) -> None:
        """Apply enabled/disabled state to every widget from the tracked flags."""
        base = "normal" if self._unlocked else "disabled"
        self.write_subs_switch.configure(state=base)
        self.write_auto_switch.configure(state=base)

        # Languages only matter when we're actually fetching subtitles.
        langs_state = (
            "normal" if (self._unlocked and self._any_write_on()) else "disabled"
        )
        self.langs_entry.configure(state=langs_state)

        # Embedding needs a video container; extract-audio-only has none.
        extract_audio = self._is_extract_audio_on()
        embed_state = (
            "normal" if (self._unlocked and not extract_audio) else "disabled"
        )
        self.embed_switch.configure(state=embed_state)

        if extract_audio:
            self.embed_note.grid(
                row=self._embed_note_row,
                column=0,
                columnspan=3,
                padx=12,
                pady=(0, 4),
                sticky="w",
            )
        else:
            self.embed_note.grid_remove()

    def set_controls_enabled(self, enabled: bool) -> None:
        """Lock/unlock the tab while a run is in progress."""
        self._unlocked = enabled
        self._refresh_states()

    # -- Accessors ---------------------------------------------------------
    def get_args(self) -> list[str]:
        """The yt-dlp flags for the Subtitles tab."""
        args: list[str] = []

        if self.write_subs_var.get():
            args.append("--write-subs")
        if self.write_auto_var.get():
            args.append("--write-auto-subs")

        langs = self.langs_var.get().strip()
        if langs and self._any_write_on():
            args += ["--sub-langs", langs]

        # Drop --embed-subs when extract-audio is on: there is no video container
        # to embed into, so sending it would only produce a yt-dlp error.
        if self.embed_var.get() and not self._is_extract_audio_on():
            args.append("--embed-subs")

        return args
