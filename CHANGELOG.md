# Changelog

## [Unreleased]

### Phase 1 — 2026-07-31
- Real `CommandRunner`: launches yt-dlp in a background thread, streams stdout line
  by line (uses `--newline` so progress updates arrive as discrete lines), parses
  `[download] NN.N%` lines into a float via regex, and reports back through
  `on_output` / `on_progress` / `on_done` callbacks. `stop()` terminates the process
  with a force-kill fallback; missing-executable and launch errors are handled without
  crashing.
- Runner reuses the Phase 0 dependency detection via a new
  `resolve_ytdlp_command()` helper (prefers the `yt-dlp` executable on PATH, falls
  back to `python -u -m yt_dlp`).
- Core tab (`app/ui/tabs/core_tab.py`): URL entry with non-empty validation, format
  preset dropdown (Best / ≤1080p / ≤720p / custom `-f`), "List available formats"
  (`yt-dlp -F`), output-template dropdown (with custom option), and a download-folder
  entry with a Browse button defaulting to the user's Downloads folder.
- Main window: determinate `CTkProgressBar` + status label driven by parsed progress,
  a collapsible raw-log panel (collapsed by default), and Run/Stop buttons wired to the
  runner. All worker-thread callbacks are marshaled to the main thread through a
  thread-safe queue polled via `after()`.

### Phase 0 — 2026-07-31
- Initial repo scaffold
- Dependency check for yt-dlp and ffmpeg on startup
- Main window shell with empty tab bar, log console placeholder, Run/Stop buttons (disabled
  until Phase 1 wires a real command)
