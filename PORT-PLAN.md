# ytdlp-gui-toolkit — Build Plan

## Status legend
[ ] Not started   [~] In progress   [x] Done

## Phases

- [x] Phase 0 — Repo scaffold, plan files, dependency check, main window shell
- [x] Phase 1 — Core tab: URL input, format selection, output template, download path,
                real subprocess runner, parsed progress bar (from yt-dlp's stdout, not
                just raw scrolling text) with a collapsible raw-log panel underneath
- [x] Phase 2 — Audio tab: extract-audio, audio format, audio quality
- [x] Phase 3 — Playlist tab: item ranges, playlist toggle, download archive
- [ ] Phase 4 — Subtitles tab: write subs/auto-subs, sub languages, embed subs
- [ ] Phase 5 — Advanced tab: rate limit, sleep interval, cookies-from-browser
                (with explicit UI warning it reads the browser's credential store),
                SponsorBlock mark/remove
- [ ] Phase 6 — Command preview panel, presets (save/load JSON), copy-command button,
                yt-dlp self-update button, PORT-PARITY.md reaches 100%
- [ ] Phase 7 (optional, future) — PyInstaller packaging into standalone .exe

## Notes for future phases
- Each phase prompt must be self-contained and runnable in a fresh Claude Code session.
- Before starting work, read PORT-PLAN.md, PORT-PARITY.md, and CHANGELOG.md.
- On completion: tick this file's checklist, append a dated CHANGELOG.md entry, and
  update PORT-PARITY.md with any newly wired yt-dlp flags.
- End each phase at a working, runnable state — no stubs, no partially wired tabs left
  visible in the UI (hide/disable anything not yet implemented).
- On completion, also add a short section to README.md describing the feature(s) that
  phase implemented (what tab/control was added, what it does). README.md should build up
  incrementally, phase by phase, so by the end it is a complete description of the tool
  with no separate "write the docs" pass needed.
