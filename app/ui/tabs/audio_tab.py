"""Audio tab: extract-audio-only, audio format, and audio quality.

Follows the pattern established by ``core_tab.py`` in Phase 1: the tab owns its
widgets and exposes :meth:`get_args` returning the yt-dlp flags for its state.
MainWindow concatenates each tab's args when Run is hit.

When "Extract audio only" is off, none of the other controls affect the built
command *and* they are visually disabled, so a user can't set an audio format
that silently does nothing.
"""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from app import config


class AudioTab:
    """Builds and owns the Audio tab widgets inside a parent frame."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_extract_change: Callable[[], None],
    ) -> None:
        """Create the Audio tab.

        Args:
            master: The tab frame to build into (from ``CTkTabview.tab(...)``).
            on_extract_change: Called whenever the extract-audio toggle flips, so
                the window can grey/re-enable the Core tab's video-format controls
                (which don't apply when downloading audio only).
        """
        self._master = master
        self._on_extract_change = on_extract_change

        # Run-lock state (False while a download is in progress) and the
        # extract-audio sub-state together decide each widget's enabled state.
        self._unlocked = True

        master.grid_columnconfigure(1, weight=1)
        row = 0

        # -- Extract audio toggle -----------------------------------------
        self.extract_var = ctk.BooleanVar(value=False)
        self.extract_switch = ctk.CTkSwitch(
            master,
            text="Extract audio only  (-x)",
            variable=self.extract_var,
            command=self._on_toggle,
        )
        self.extract_switch.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(14, 8), sticky="w"
        )
        row += 1

        # -- Audio format --------------------------------------------------
        ctk.CTkLabel(master, text="Audio format:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.format_menu = ctk.CTkOptionMenu(
            master, values=list(config.AUDIO_FORMATS)
        )
        self.format_menu.set(config.AUDIO_FORMATS[0])  # "best"
        self.format_menu.grid(row=row, column=1, padx=(0, 12), pady=6, sticky="w")
        row += 1

        # -- Audio quality -------------------------------------------------
        ctk.CTkLabel(master, text="Audio quality:").grid(
            row=row, column=0, padx=(12, 6), pady=6, sticky="w"
        )
        self.quality_menu = ctk.CTkOptionMenu(
            master,
            values=list(config.AUDIO_QUALITY_PRESETS.keys()),
            command=lambda _: self._on_quality_change(),
        )
        # Default to "Good (5, default)".
        self.quality_menu.set(list(config.AUDIO_QUALITY_PRESETS.keys())[1])
        self.quality_menu.grid(row=row, column=1, padx=(0, 12), pady=6, sticky="w")
        row += 1

        # Custom bitrate entry (revealed only for "Custom bitrate...").
        self.custom_bitrate_var = ctk.StringVar()
        self.custom_bitrate_entry = ctk.CTkEntry(
            master,
            textvariable=self.custom_bitrate_var,
            placeholder_text="Bitrate, e.g. 128K, 192K, 320K",
        )
        self._custom_bitrate_row = row
        row += 1

        # -- Inline help ---------------------------------------------------
        self.hint_label = ctk.CTkLabel(
            master,
            text="Turn on 'Extract audio only' to convert downloads to an audio file.",
            text_color="gray",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self.hint_label.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(8, 6), sticky="w"
        )

        self._refresh_states()

    # -- Widget callbacks --------------------------------------------------
    def _on_toggle(self) -> None:
        self._refresh_states()
        self._on_extract_change()

    def _on_quality_change(self) -> None:
        self._apply_custom_bitrate_visibility()

    def _apply_custom_bitrate_visibility(self) -> None:
        show = (
            self.quality_menu.get() == config.CUSTOM_BITRATE_LABEL
            and self.extract_var.get()
        )
        if show:
            self.custom_bitrate_entry.grid(
                row=self._custom_bitrate_row,
                column=1,
                padx=(0, 12),
                pady=(0, 6),
                sticky="ew",
            )
        else:
            self.custom_bitrate_entry.grid_remove()

    # -- State management --------------------------------------------------
    def _refresh_states(self) -> None:
        """Apply enabled/disabled state to every widget.

        The extract switch follows the run-lock only; the format/quality controls
        additionally require extract-audio to be on.
        """
        extract_on = self.extract_var.get()

        self.extract_switch.configure(state="normal" if self._unlocked else "disabled")

        sub_state = "normal" if (self._unlocked and extract_on) else "disabled"
        for widget in (
            self.format_menu,
            self.quality_menu,
            self.custom_bitrate_entry,
        ):
            widget.configure(state=sub_state)

        self._apply_custom_bitrate_visibility()

    def set_controls_enabled(self, enabled: bool) -> None:
        """Lock/unlock the tab while a run is in progress."""
        self._unlocked = enabled
        self._refresh_states()

    # -- Public accessors --------------------------------------------------
    def is_extract_on(self) -> bool:
        """True when audio-only extraction is enabled."""
        return bool(self.extract_var.get())

    def _selected_quality(self) -> str:
        label = self.quality_menu.get()
        if label == config.CUSTOM_BITRATE_LABEL:
            return self.custom_bitrate_var.get().strip()
        return config.AUDIO_QUALITY_PRESETS.get(label, "")

    def get_args(self) -> list[str]:
        """The yt-dlp flags for the Audio tab (empty when extract-audio is off)."""
        if not self.extract_var.get():
            return []

        args = ["-x", "--audio-format", self.format_menu.get()]

        quality = self._selected_quality()
        if quality:
            args += ["--audio-quality", quality]

        return args
