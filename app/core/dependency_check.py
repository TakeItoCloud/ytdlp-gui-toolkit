"""Startup dependency checks for yt-dlp and ffmpeg.

The app shells out to the ``yt-dlp`` CLI (Phase 1+) and relies on ``ffmpeg``
being on PATH for merging/remuxing/audio extraction. Neither is bundled — the
user installs them separately. This module detects their presence so the app
can warn clearly at startup instead of failing cryptically mid-download.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass

from app.config import FFMPEG_CLI, YTDLP_CLI


@dataclass(frozen=True)
class DependencyStatus:
    """Result of a single dependency probe."""

    name: str
    found: bool
    detail: str


def _check_ytdlp() -> DependencyStatus:
    """yt-dlp counts as present if importable as a library OR on PATH as a CLI."""
    on_path = shutil.which(YTDLP_CLI)
    importable = importlib.util.find_spec("yt_dlp") is not None

    if on_path and importable:
        return DependencyStatus(
            YTDLP_CLI, True, f"found on PATH ({on_path}) and importable"
        )
    if on_path:
        return DependencyStatus(YTDLP_CLI, True, f"found on PATH ({on_path})")
    if importable:
        return DependencyStatus(YTDLP_CLI, True, "found as importable Python module")
    return DependencyStatus(YTDLP_CLI, False, "not found on PATH or as a Python module")


def _check_ffmpeg() -> DependencyStatus:
    """ffmpeg must be an executable on PATH."""
    on_path = shutil.which(FFMPEG_CLI)
    if on_path:
        return DependencyStatus(FFMPEG_CLI, True, f"found on PATH ({on_path})")
    return DependencyStatus(FFMPEG_CLI, False, "not found on PATH")


def check_dependencies() -> list[DependencyStatus]:
    """Probe every external dependency the app needs. UI-agnostic."""
    return [_check_ytdlp(), _check_ffmpeg()]


def missing_dependencies() -> list[DependencyStatus]:
    """Return only the dependencies that were not found."""
    return [dep for dep in check_dependencies() if not dep.found]


def resolve_ytdlp_command() -> list[str] | None:
    """Return the base command tokens used to invoke yt-dlp, or None if absent.

    Reuses the same detection order as :func:`_check_ytdlp` so callers (e.g. the
    subprocess runner) don't duplicate the logic:

    * If the ``yt-dlp`` executable is on PATH, use it directly.
    * Otherwise, if the ``yt_dlp`` module is importable, invoke it via the
      current interpreter: ``python -u -m yt_dlp`` (``-u`` keeps stdout
      unbuffered so progress streams line by line).
    * If neither is available, return ``None``.
    """
    on_path = shutil.which(YTDLP_CLI)
    if on_path:
        return [on_path]
    if importlib.util.find_spec("yt_dlp") is not None:
        return [sys.executable, "-u", "-m", "yt_dlp"]
    return None


# --- Install hints shown to the user when a dependency is missing -----------
INSTALL_HINTS: dict[str, str] = {
    YTDLP_CLI: (
        "Install yt-dlp with pip:\n"
        "    python -m pip install -U yt-dlp\n"
        "or download the standalone binary from:\n"
        "    https://github.com/yt-dlp/yt-dlp/releases"
    ),
    FFMPEG_CLI: (
        "Install ffmpeg and make sure it is on your PATH:\n"
        "    Windows (winget):  winget install Gyan.FFmpeg\n"
        "    Windows (choco):   choco install ffmpeg\n"
        "or download from:\n"
        "    https://www.gyan.dev/ffmpeg/builds/  (Windows)\n"
        "    https://ffmpeg.org/download.html      (all platforms)"
    ),
}


def format_missing_message(missing: list[DependencyStatus]) -> str:
    """Build a human-readable warning body listing what's missing + how to fix it."""
    lines = [
        "The following required tools were not found:",
        "",
    ]
    for dep in missing:
        lines.append(f"  - {dep.name}: {dep.detail}")
    lines.append("")
    for dep in missing:
        hint = INSTALL_HINTS.get(dep.name)
        if hint:
            lines.append(f"How to install {dep.name}:")
            lines.append(hint)
            lines.append("")
    lines.append(
        "You can still open the app, but downloads will fail until these are installed."
    )
    return "\n".join(lines).rstrip()
