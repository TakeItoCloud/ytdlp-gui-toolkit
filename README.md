# ytdlp-gui-toolkit

A lightweight desktop GUI that wraps the [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
command-line tool. Instead of memorizing flags, you build a `yt-dlp` command from
tabbed sections in a small [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
window; the app runs `yt-dlp` as a subprocess and streams its progress and output
back into the UI. It's a personal tool for Windows, run as a script.

## Requirements

- **Python 3.11+**
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — installed separately (via `pip`, or
  as the standalone binary on your PATH)
- **[ffmpeg](https://ffmpeg.org/)** — on your PATH (needed for merging, remuxing, and
  audio extraction)

`yt-dlp` and `ffmpeg` are **not** bundled. The app checks for both at startup and warns
clearly if either is missing.

## Setup

```bash
# from the repo root
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

python -m pip install -r requirements.txt
```

Make sure `ffmpeg` is installed and on your PATH (e.g. `winget install Gyan.FFmpeg`
on Windows).

## Run

```bash
python main.py
```

## Features

Features are built up phase by phase (see `PORT-PLAN.md`).

### Phase 0 — Scaffold & startup checks
- Main window shell with a tab bar for the five planned sections (Core, Audio,
  Playlist, Subtitles, Advanced — empty for now), a read-only log console, and
  Run/Stop buttons (disabled until a real command is wired in Phase 1).
- **Startup dependency check**: on launch, the app verifies that `yt-dlp` (importable
  as a Python module or found on PATH) and `ffmpeg` (on PATH) are present. Results are
  written to the log console, and a dialog with install instructions appears if
  anything is missing — no silent failures.

### Phase 1 — Core tab & real downloads
The app can now actually download videos. The **Core** tab drives a real `yt-dlp`
subprocess:
- **URL** field for a single video or playlist URL (Run stays disabled until a URL is
  entered).
- **Format** dropdown mapping friendly labels to real `-f` values — *Best
  (video+audio, merged)*, *Best up to 1080p*, *Best up to 720p*, or a *Custom format
  string...* option that reveals a free-text `-f` entry. A **List available formats**
  button runs `yt-dlp -F <url>` and shows the table in the raw-log panel.
- **Output template** dropdown for common `-o` patterns (`%(title)s.%(ext)s`,
  `%(uploader)s/%(title)s.%(ext)s`, `%(upload_date)s - %(title)s.%(ext)s`) plus a
  custom option.
- **Download folder** entry with a **Browse...** picker, defaulting to your Downloads
  folder.
- **Run / Stop**: Run launches yt-dlp in a background thread; Stop terminates it
  cleanly (with a force-kill fallback).
- **Progress bar + status**: yt-dlp's `[download] NN.N%` output is parsed into a real
  determinate progress bar, with a status label that shows the live percentage and
  switches to non-progress steps (e.g. `[Merger] Merging formats...`) as they happen.
- **Collapsible raw log**: the full yt-dlp output is available behind a *Show raw log*
  toggle (collapsed by default) for debugging.

### Phase 2 — Audio tab (extract audio)
The **Audio** tab turns a download into an audio-only extraction:
- **Extract audio only** toggle (`-x`). While it's off, the rest of the Audio tab is
  disabled so its settings can't silently do nothing.
- **Audio format** (`--audio-format`): `best`, `mp3`, `m4a`, `flac`, `wav`, `opus`,
  `vorbis`, `aac`, or `alac`.
- **Audio quality** (`--audio-quality`): presets *Best (0)*, *Good (5)*, *Smaller file
  (9)*, or a *Custom bitrate...* entry for values like `128K` / `192K` / `320K`.
- Turning on extract-audio greys out the Core tab's video **Format** controls (with an
  inline note) and drops `-f` from the command, letting yt-dlp choose the best audio
  source rather than sending a conflicting video selector. The output template and
  download folder from the Core tab still apply.
