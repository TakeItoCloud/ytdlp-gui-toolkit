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

# --- Audio tab: --audio-format choices --------------------------------------
# Passed verbatim to yt-dlp's --audio-format. "best" keeps the best available
# audio without re-encoding (yt-dlp's own default).
AUDIO_FORMATS: tuple[str, ...] = (
    "best",
    "mp3",
    "m4a",
    "flac",
    "wav",
    "opus",
    "vorbis",
    "aac",
    "alac",
)

# --- Audio tab: --audio-quality presets -------------------------------------
# yt-dlp's --audio-quality takes a 0 (best) - 10 (worst) VBR scale OR a specific
# bitrate like "128K". Presets map to VBR numbers; the custom option reveals a
# free-text entry for a bitrate.
CUSTOM_BITRATE_LABEL = "Custom bitrate..."
AUDIO_QUALITY_PRESETS: dict[str, str] = {
    "Best (0)": "0",
    "Good (5, default)": "5",
    "Smaller file (9)": "9",
    CUSTOM_BITRATE_LABEL: "",
}

# --- Playlist tab: playlist handling ----------------------------------------
# Human label -> yt-dlp flag. "Auto" adds nothing (yt-dlp's own default). The
# "Video only" sentinel also greys out the playlist-items field.
PLAYLIST_NO_PLAYLIST_LABEL = "Video only, ignore playlist"
PLAYLIST_HANDLING: dict[str, str] = {
    "Auto (yt-dlp default)": "",
    PLAYLIST_NO_PLAYLIST_LABEL: "--no-playlist",
    "Full playlist": "--yes-playlist",
}

# --- Playlist tab: download archive -----------------------------------------
# Default filename suggested (in the Core tab's download folder) when the
# download-archive toggle is switched on with an empty path.
DEFAULT_ARCHIVE_FILENAME = "archive.txt"

# --- Advanced tab: cookies-from-browser -------------------------------------
# Browsers yt-dlp can read cookies from (--cookies-from-browser).
COOKIE_BROWSERS: tuple[str, ...] = (
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "brave",
    "opera",
    "safari",
    "vivaldi",
    "whale",
)

# Shown as a visible label next to the cookies control (not a one-time dialog):
# this flag reads the browser's saved credential store, so the warning stays on
# screen whenever the tab is open.
COOKIES_WARNING = (
    "Reads cookies directly from your browser's saved session / credential store. "
    "Only use this for content you're logged into and want yt-dlp to access on "
    "your behalf."
)

# --- Advanced tab: SponsorBlock ---------------------------------------------
# Standard SponsorBlock categories. Each can be marked (chaptered) and/or removed
# (cut) independently; the comma-joined lists feed --sponsorblock-mark /
# --sponsorblock-remove.
SPONSORBLOCK_CATEGORIES: tuple[str, ...] = (
    "sponsor",
    "intro",
    "outro",
    "selfpromo",
    "preview",
    "filler",
    "interaction",
    "music_offtopic",
)
