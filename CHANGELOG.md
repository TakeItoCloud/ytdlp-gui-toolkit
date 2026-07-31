# Changelog

## [Unreleased]

### Phase 4 — 2026-07-31
- Subtitles tab (`app/ui/tabs/subtitles_tab.py`): "Write subtitles" (`--write-subs`)
  and "Write auto-generated subtitles" (`--write-auto-subs`) toggles (independent, both
  may be on), a subtitle-languages field (`--sub-langs`, free-text with a loose sanity
  check + inline warning — no full-grammar parsing), and an "Embed subtitles into video"
  toggle (`--embed-subs`).
- Command building extended with `SubtitlesTab.get_args()`, concatenated after the
  Core/Audio/Playlist args; the tab is included in the run-lock.
- Interactions: the languages field greys out (and `--sub-langs` is dropped) unless at
  least one write-subtitles toggle is on. `--embed-subs` greys out with an inline note —
  and is dropped from the command — when the Audio tab's extract-audio mode is on, since
  there is no video container to embed into (one-directional dependency; write-subs and
  sub-langs remain valid alongside audio extraction).

### Phase 3 — 2026-07-31
- Playlist tab (`app/ui/tabs/playlist_tab.py`): playlist handling dropdown (Auto /
  `--no-playlist` / `--yes-playlist`), playlist items field (`-I`, free-text range
  syntax with a loose `[0-9,:\-]` sanity check and inline warning — no full-grammar
  parsing), and a download-archive toggle (`--download-archive`) with a path entry and
  Browse (asksaveasfilename, so an existing or new file both work). The archive path
  defaults to `archive.txt` in the Core tab's download folder when first enabled.
- Command building extended with `PlaylistTab.get_args()`, concatenated after the Core
  and Audio tab args.
- Interaction: selecting "Video only, ignore playlist" greys out the playlist-items
  field and drops `-I` from the built command. The download archive is file-type
  agnostic, so it coexists with extract-audio mode with no special handling.

### Phase 2 — 2026-07-31
- Audio tab (`app/ui/tabs/audio_tab.py`): "Extract audio only" toggle (`-x`), audio
  format dropdown (`--audio-format`: best/mp3/m4a/flac/wav/opus/vorbis/aac/alac), and
  audio quality (`--audio-quality`) via presets (Best 0 / Good 5 / Smaller 9) plus a
  "Custom bitrate..." entry for values like `128K`. When extract-audio is off, the
  format/quality controls are visually disabled and contribute nothing to the command.
- Command building extended: each tab exposes its own args method
  (`AudioTab.get_args()`), and the Run handler concatenates
  `core.build_download_args() + audio.get_args() + [url]`.
- Core/Audio interaction: turning on extract-audio greys out the Core tab's video
  format controls (with an inline note) and suppresses `-f` from the built command, so
  yt-dlp picks the best audio source itself instead of receiving a conflicting video
  selector. Toggling off restores them.

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
