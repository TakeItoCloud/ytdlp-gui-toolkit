"""Subprocess wrapper around the yt-dlp CLI.

Launches yt-dlp in a background thread, streams its stdout line by line, parses
yt-dlp's ``[download] NN.N%`` progress lines into a float, and reports back to
the UI via callbacks. Cancellation is supported via :meth:`stop`.

The callbacks are invoked *from the worker thread*. Tkinter widgets are not
thread-safe, so the UI layer is responsible for marshaling these callbacks back
onto the main loop (this module stays UI-agnostic).
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
from collections.abc import Callable

from app.core.dependency_check import resolve_ytdlp_command

# yt-dlp download progress lines look like (spacing varies a lot):
#   [download]  45.2% of   12.34MiB at    1.23MiB/s ETA 00:08
#   [download] 100% of 12.34MiB in 00:10
#   [download]   0.0% of ~12.34MiB at  Unknown B/s ETA Unknown
# Match the percentage regardless of surrounding whitespace.
_PROGRESS_RE = re.compile(r"^\[download\]\s+(\d{1,3}(?:\.\d+)?)%")

# How long to wait after terminate() before force-killing a stubborn process.
_KILL_GRACE_SECONDS = 5.0


class CommandRunner:
    """Runs a yt-dlp command as a subprocess and streams its output.

    A single runner handles one subprocess at a time. Call :meth:`run` to start;
    it returns immediately while work continues on a background thread. Use
    :meth:`is_running` to guard against overlapping runs.
    """

    def __init__(self) -> None:
        self._proc: subprocess.Popen[str] | None = None
        self._thread: threading.Thread | None = None
        self._stopped = False

    # -- Public API --------------------------------------------------------
    def is_running(self) -> bool:
        """True while a subprocess is active."""
        return self._proc is not None and self._proc.poll() is None

    def run(
        self,
        args: list[str],
        on_output: Callable[[str], None],
        on_progress: Callable[[float | None, str], None],
        on_done: Callable[[int], None],
    ) -> None:
        """Launch yt-dlp with ``args`` and stream output back via callbacks.

        Args:
            args: The complete yt-dlp argument list (flags plus the target URL
                as the final element). The yt-dlp executable itself is prepended
                automatically; do not include it.
            on_output: Called with each raw stdout line (stderr is merged in).
            on_progress: Called for every line. If the line is a download
                progress line, the first argument is the parsed percentage
                (0.0-100.0); otherwise it is ``None`` (a status line the UI can
                display without moving the progress bar).
            on_done: Called with the process return code when it exits (or a
                synthetic non-zero code if the process could not be launched).
        """
        if self.is_running():
            raise RuntimeError("A yt-dlp process is already running.")

        base = resolve_ytdlp_command()
        if base is None:
            on_output("ERROR: yt-dlp is not available (not on PATH or importable).")
            on_done(127)
            return

        # --newline makes yt-dlp emit each progress update on its own line
        # (instead of overwriting one line with '\r'), so line-based reading
        # streams progress instead of buffering until the end.
        cmd = [*base, "--newline", *args]

        self._stopped = False
        self._thread = threading.Thread(
            target=self._worker,
            args=(cmd, on_output, on_progress, on_done),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Terminate the running subprocess, with a force-kill fallback."""
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        self._stopped = True
        try:
            proc.terminate()
        except Exception:
            pass
        # Force-kill after a grace period, off the caller's thread so the UI
        # never blocks waiting for a stubborn process to die.
        threading.Thread(
            target=self._force_kill_after, args=(proc,), daemon=True
        ).start()

    # -- Internals ---------------------------------------------------------
    def _worker(
        self,
        cmd: list[str],
        on_output: Callable[[str], None],
        on_progress: Callable[[float | None, str], None],
        on_done: Callable[[int], None],
    ) -> None:
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            on_output("ERROR: yt-dlp executable disappeared before launch.")
            on_done(127)
            return
        except Exception as exc:  # pragma: no cover - defensive
            on_output(f"ERROR launching yt-dlp: {exc}")
            on_done(1)
            return

        try:
            assert self._proc.stdout is not None
            for raw in self._proc.stdout:
                line = raw.rstrip("\r\n")
                if not line:
                    continue
                on_output(line)
                match = _PROGRESS_RE.match(line)
                if match:
                    on_progress(float(match.group(1)), line)
                else:
                    on_progress(None, line)
            returncode = self._proc.wait()
        except Exception as exc:  # pragma: no cover - defensive
            on_output(f"ERROR while reading yt-dlp output: {exc}")
            returncode = 1
        finally:
            proc = self._proc
            self._proc = None

        if self._stopped:
            on_output("[stopped] Download cancelled by user.")
        on_done(returncode)

    def _force_kill_after(self, proc: subprocess.Popen[str]) -> None:
        deadline = _KILL_GRACE_SECONDS
        step = 0.1
        waited = 0.0
        while waited < deadline:
            if proc.poll() is not None:
                return
            time.sleep(step)
            waited += step
        if proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
