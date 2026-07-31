# yt-dlp Flag Parity Tracker

Tracks GUI coverage of yt-dlp CLI options. Status: `Not wired` / `Wired` / `Wired (partial)`.

## Core / Format
| Flag | Status | Phase |
|---|---|---|
| -f / --format | Wired | 1 |
| -F / --list-formats | Wired | 1 |
| -o / --output | Wired | 1 |
| -P / --paths | Wired | 1 |

## Audio
| Flag | Status | Phase |
|---|---|---|
| -x / --extract-audio | Wired | 2 |
| --audio-format | Wired | 2 |
| --audio-quality | Wired | 2 |

## Playlist
| Flag | Status | Phase |
|---|---|---|
| -I / --playlist-items | Wired | 3 |
| --no-playlist / --yes-playlist | Wired | 3 |
| --download-archive | Wired | 3 |

## Subtitles
| Flag | Status | Phase |
|---|---|---|
| --write-subs | Wired | 4 |
| --write-auto-subs | Wired | 4 |
| --sub-langs | Wired | 4 |
| --embed-subs | Wired | 4 |

## Advanced
| Flag | Status | Phase |
|---|---|---|
| -r / --limit-rate | Wired | 5 |
| --sleep-interval | Wired | 5 |
| --cookies-from-browser | Wired | 5 |
| --sponsorblock-mark | Wired | 5 |
| --sponsorblock-remove | Wired | 5 |

## Meta
| Flag | Status | Phase |
|---|---|---|
| -U / --update | Not wired | 6 |
| Progress bar parsing (from yt-dlp's `[download] NN.N%` stdout lines, into a real progress widget — not just raw log scroll) | Wired | 1 |
