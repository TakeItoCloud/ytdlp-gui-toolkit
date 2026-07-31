"""App-wide constants: window sizing, theme, and identity.

Kept intentionally small in Phase 0. Future phases add settings here (default
download paths, preset locations, etc.) rather than scattering magic values
through the UI code.
"""

# --- Identity ---------------------------------------------------------------
APP_NAME = "ytdlp-gui-toolkit"
APP_TITLE = "yt-dlp GUI Toolkit"

# --- Window -----------------------------------------------------------------
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 620
MIN_WINDOW_WIDTH = 720
MIN_WINDOW_HEIGHT = 480

# --- Theme ------------------------------------------------------------------
# CustomTkinter appearance mode: "System", "Dark", or "Light".
APPEARANCE_MODE = "System"
# Built-in color theme: "blue", "dark-blue", or "green".
COLOR_THEME = "blue"

# --- Tabs -------------------------------------------------------------------
# Placeholder tab order for the main window. Content is wired in later phases.
TAB_NAMES = ("Core", "Audio", "Playlist", "Subtitles", "Advanced")

# --- External dependencies --------------------------------------------------
# Commands the app expects to find at startup (see core.dependency_check).
YTDLP_CLI = "yt-dlp"
FFMPEG_CLI = "ffmpeg"

# --- Core tab: format presets -----------------------------------------------
# Human label -> real yt-dlp `-f` value. The sentinel below reveals a free-text
# entry instead of mapping to a fixed value.
CUSTOM_FORMAT_LABEL = "Custom format string..."
FORMAT_PRESETS: dict[str, str] = {
    "Best (video+audio, merged)": "bv*+ba/b",
    "Best up to 1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "Best up to 720p": "bv*[height<=720]+ba/b[height<=720]",
    CUSTOM_FORMAT_LABEL: "",
}

# --- Core tab: output template (-o) presets ---------------------------------
CUSTOM_OUTPUT_LABEL = "Custom..."
OUTPUT_PRESETS: dict[str, str] = {
    "%(title)s.%(ext)s": "%(title)s.%(ext)s",
    "%(uploader)s/%(title)s.%(ext)s": "%(uploader)s/%(title)s.%(ext)s",
    "%(upload_date)s - %(title)s.%(ext)s": "%(upload_date)s - %(title)s.%(ext)s",
    CUSTOM_OUTPUT_LABEL: "",
}
