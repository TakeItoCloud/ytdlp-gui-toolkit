"""Advanced tab: rate limit, sleep interval, cookies-from-browser, SponsorBlock.

Follows the per-tab pattern from Phases 1-4: the tab owns its widgets and exposes
:meth:`get_args` returning the yt-dlp flags for its state. MainWindow concatenates
each tab's args when Run is hit.

The controls live inside a scrollable frame because this tab holds noticeably
more widgets than the others (a full SponsorBlock category grid plus the
rate/sleep/cookies controls).
"""

from __future__ import annotations

import re

import customtkinter as ctk

from app import config

# Loose numeric sanity check for the sleep interval (int or float seconds); the
# value is still passed to yt-dlp verbatim, this only drives an inline warning.
_SLEEP_NUMERIC_RE = re.compile(r"^\d*\.?\d*$")


class AdvancedTab:
    """Builds and owns the Advanced tab widgets inside a parent frame."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Create the Advanced tab.

        Args:
            master: The tab frame to build into (from ``CTkTabview.tab(...)``).
        """
        self._master = master
        self._unlocked = True

        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(0, weight=1)

        # Scrollable host so the SponsorBlock grid never overflows the tab.
        self.scroll = ctk.CTkScrollableFrame(master, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(1, weight=1)

        parent = self.scroll
        row = 0

        # -- Rate limit ----------------------------------------------------
        self.rate_var = ctk.BooleanVar(value=False)
        self.rate_switch = ctk.CTkSwitch(
            parent,
            text="Limit download rate  (-r)",
            variable=self.rate_var,
            command=self._refresh_states,
        )
        self.rate_switch.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(14, 2), sticky="w"
        )
        row += 1

        ctk.CTkLabel(parent, text="Max rate:").grid(
            row=row, column=0, padx=(12, 6), pady=(0, 8), sticky="w"
        )
        self.rate_value_var = ctk.StringVar()
        self.rate_entry = ctk.CTkEntry(
            parent,
            textvariable=self.rate_value_var,
            placeholder_text="e.g. 2M  (50K, 4.2M ...)",
        )
        self.rate_entry.grid(row=row, column=1, padx=(0, 12), pady=(0, 8), sticky="w")
        row += 1

        # -- Sleep interval -----------------------------------------------
        self.sleep_var = ctk.BooleanVar(value=False)
        self.sleep_switch = ctk.CTkSwitch(
            parent,
            text="Sleep between downloads  (--sleep-interval)",
            variable=self.sleep_var,
            command=self._refresh_states,
        )
        self.sleep_switch.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(6, 2), sticky="w"
        )
        row += 1

        ctk.CTkLabel(parent, text="Seconds:").grid(
            row=row, column=0, padx=(12, 6), pady=(0, 2), sticky="w"
        )
        self.sleep_value_var = ctk.StringVar()
        self.sleep_value_var.trace_add("write", lambda *_: self._validate_sleep())
        self.sleep_entry = ctk.CTkEntry(
            parent,
            textvariable=self.sleep_value_var,
            placeholder_text="e.g. 3  (integer or decimal seconds)",
        )
        self.sleep_entry.grid(row=row, column=1, padx=(0, 12), pady=(0, 2), sticky="w")
        row += 1
        # NOTE: --max-sleep-interval (a random range upper bound) is intentionally
        # out of scope for this tool; only the single --sleep-interval is exposed.

        self.sleep_warning = ctk.CTkLabel(
            parent,
            text="",
            text_color="#e06c50",
            anchor="w",
            font=ctk.CTkFont(size=11),
        )
        self._sleep_warning_row = row
        row += 1

        # -- Cookies from browser -----------------------------------------
        self.cookies_var = ctk.BooleanVar(value=False)
        self.cookies_switch = ctk.CTkSwitch(
            parent,
            text="Use cookies from browser  (--cookies-from-browser)",
            variable=self.cookies_var,
            command=self._refresh_states,
        )
        self.cookies_switch.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(10, 2), sticky="w"
        )
        row += 1

        ctk.CTkLabel(parent, text="Browser:").grid(
            row=row, column=0, padx=(12, 6), pady=2, sticky="w"
        )
        self.browser_menu = ctk.CTkOptionMenu(
            parent, values=list(config.COOKIE_BROWSERS)
        )
        self.browser_menu.set(config.COOKIE_BROWSERS[0])
        self.browser_menu.grid(row=row, column=1, padx=(0, 12), pady=2, sticky="w")
        row += 1

        # Always-visible credential-store warning (not a dismissible dialog).
        self.cookies_warning = ctk.CTkLabel(
            parent,
            text=config.COOKIES_WARNING,
            text_color="#d18b2c",
            anchor="w",
            justify="left",
            wraplength=740,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.cookies_warning.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(2, 8), sticky="w"
        )
        row += 1

        # -- SponsorBlock --------------------------------------------------
        self.sponsorblock_var = ctk.BooleanVar(value=False)
        self.sponsorblock_switch = ctk.CTkSwitch(
            parent,
            text="Enable SponsorBlock  (mark / remove segments)",
            variable=self.sponsorblock_var,
            command=self._refresh_states,
        )
        self.sponsorblock_switch.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(8, 2), sticky="w"
        )
        row += 1

        # Category grid: one row per category with Mark and Remove checkboxes.
        self.sb_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.sb_frame.grid(
            row=row, column=0, columnspan=2, padx=12, pady=(2, 8), sticky="w"
        )
        header_cat = ctk.CTkLabel(
            self.sb_frame, text="Category", font=ctk.CTkFont(size=11, weight="bold")
        )
        header_cat.grid(row=0, column=0, padx=(0, 24), pady=(0, 4), sticky="w")
        header_mark = ctk.CTkLabel(
            self.sb_frame, text="Mark", font=ctk.CTkFont(size=11, weight="bold")
        )
        header_mark.grid(row=0, column=1, padx=(0, 20), pady=(0, 4))
        header_remove = ctk.CTkLabel(
            self.sb_frame, text="Remove", font=ctk.CTkFont(size=11, weight="bold")
        )
        header_remove.grid(row=0, column=2, padx=(0, 4), pady=(0, 4))

        self.mark_vars: dict[str, ctk.BooleanVar] = {}
        self.remove_vars: dict[str, ctk.BooleanVar] = {}
        self._sb_mark_boxes: list[ctk.CTkCheckBox] = []
        self._sb_remove_boxes: list[ctk.CTkCheckBox] = []

        for i, cat in enumerate(config.SPONSORBLOCK_CATEGORIES, start=1):
            ctk.CTkLabel(self.sb_frame, text=cat).grid(
                row=i, column=0, padx=(0, 24), pady=1, sticky="w"
            )
            mark_var = ctk.BooleanVar(value=False)
            remove_var = ctk.BooleanVar(value=False)
            self.mark_vars[cat] = mark_var
            self.remove_vars[cat] = remove_var

            mbox = ctk.CTkCheckBox(self.sb_frame, text="", variable=mark_var, width=24)
            mbox.grid(row=i, column=1, padx=(0, 20), pady=1)
            rbox = ctk.CTkCheckBox(
                self.sb_frame, text="", variable=remove_var, width=24
            )
            rbox.grid(row=i, column=2, padx=(0, 4), pady=1)
            self._sb_mark_boxes.append(mbox)
            self._sb_remove_boxes.append(rbox)
        row += 1

        self._refresh_states()

    # -- Validation --------------------------------------------------------
    def _validate_sleep(self) -> None:
        value = self.sleep_value_var.get()
        if value and not _SLEEP_NUMERIC_RE.match(value):
            self.sleep_warning.configure(
                text="Enter a number of seconds (e.g. 3 or 1.5)."
            )
            self.sleep_warning.grid(
                row=self._sleep_warning_row,
                column=1,
                padx=(0, 12),
                pady=(0, 4),
                sticky="w",
            )
        else:
            self.sleep_warning.configure(text="")
            self.sleep_warning.grid_remove()

    # -- State management --------------------------------------------------
    def _refresh_states(self) -> None:
        """Apply enabled/disabled state to every widget from the tracked flags."""
        unlocked = self._unlocked

        def state(on: bool) -> str:
            return "normal" if (unlocked and on) else "disabled"

        # Toggles follow the run-lock only.
        base = "normal" if unlocked else "disabled"
        for sw in (
            self.rate_switch,
            self.sleep_switch,
            self.cookies_switch,
            self.sponsorblock_switch,
        ):
            sw.configure(state=base)

        # Dependent controls follow their toggle too.
        self.rate_entry.configure(state=state(self.rate_var.get()))
        self.sleep_entry.configure(state=state(self.sleep_var.get()))
        self.browser_menu.configure(state=state(self.cookies_var.get()))

        sb_state = state(self.sponsorblock_var.get())
        for box in (*self._sb_mark_boxes, *self._sb_remove_boxes):
            box.configure(state=sb_state)

    def set_controls_enabled(self, enabled: bool) -> None:
        """Lock/unlock the tab while a run is in progress."""
        self._unlocked = enabled
        self._refresh_states()

    # -- Preset state (UI values, distinct from get_args CLI flags) ---------
    def get_state(self) -> dict:
        """Serialize the tab's control values for a preset."""
        return {
            "rate_on": bool(self.rate_var.get()),
            "rate_value": self.rate_value_var.get(),
            "sleep_on": bool(self.sleep_var.get()),
            "sleep_value": self.sleep_value_var.get(),
            "cookies_on": bool(self.cookies_var.get()),
            "browser": self.browser_menu.get(),
            "sponsorblock_on": bool(self.sponsorblock_var.get()),
            "mark": [c for c in config.SPONSORBLOCK_CATEGORIES if self.mark_vars[c].get()],
            "remove": [
                c for c in config.SPONSORBLOCK_CATEGORIES if self.remove_vars[c].get()
            ],
        }

    def set_state(self, state: dict) -> None:
        """Restore control values from a preset, falling back per missing key."""
        self.rate_var.set(bool(state.get("rate_on", False)))
        self.rate_value_var.set(state.get("rate_value", ""))
        self.sleep_var.set(bool(state.get("sleep_on", False)))
        self.sleep_value_var.set(state.get("sleep_value", ""))
        self.cookies_var.set(bool(state.get("cookies_on", False)))

        browser = state.get("browser", "")
        self.browser_menu.set(
            browser if browser in config.COOKIE_BROWSERS else config.COOKIE_BROWSERS[0]
        )

        self.sponsorblock_var.set(bool(state.get("sponsorblock_on", False)))
        mark = set(state.get("mark", []) or [])
        remove = set(state.get("remove", []) or [])
        for cat in config.SPONSORBLOCK_CATEGORIES:
            self.mark_vars[cat].set(cat in mark)
            self.remove_vars[cat].set(cat in remove)

        self._refresh_states()
        self._validate_sleep()

    # -- Accessors ---------------------------------------------------------
    def _checked_categories(self, vars_by_cat: dict[str, ctk.BooleanVar]) -> str:
        """Comma-join the categories whose var is checked, in config order."""
        return ",".join(
            cat for cat in config.SPONSORBLOCK_CATEGORIES if vars_by_cat[cat].get()
        )

    def get_args(self) -> list[str]:
        """The yt-dlp flags for the Advanced tab."""
        args: list[str] = []

        if self.rate_var.get():
            value = self.rate_value_var.get().strip()
            if value:
                args += ["-r", value]

        if self.sleep_var.get():
            value = self.sleep_value_var.get().strip()
            if value:
                args += ["--sleep-interval", value]

        if self.cookies_var.get():
            args += ["--cookies-from-browser", self.browser_menu.get()]

        if self.sponsorblock_var.get():
            mark = self._checked_categories(self.mark_vars)
            if mark:
                args += ["--sponsorblock-mark", mark]
            remove = self._checked_categories(self.remove_vars)
            if remove:
                args += ["--sponsorblock-remove", remove]

        return args
