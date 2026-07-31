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
