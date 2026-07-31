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
| --write-subs | Not wired | 4 |
| --write-auto-subs | Not wired | 4 |
| --sub-langs | Not wired | 4 |
| --embed-subs | Not wired | 4 |

## Advanced
| Flag | Status | Phase |
|---|---|---|
| -r / --limit-rate | Not wired | 5 |
| --sleep-interval | Not wired | 5 |
| --cookies-from-browser | Not wired | 5 |
| --sponsorblock-mark | Not wired | 5 |
| --sponsorblock-remove | Not wired | 5 |

## Meta
| Flag | Status | Phase |
|---|---|---|
| -U / --update | Not wired | 6 |
| Progress bar parsing (from yt-dlp's `[download] NN.N%` stdout lines, into a real progress widget — not just raw log scroll) | Wired | 1 |
