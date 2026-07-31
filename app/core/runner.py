"""Subprocess wrapper around the yt-dlp CLI.

Phase 0: interface stub only. The real implementation (launch yt-dlp as a
subprocess, stream stdout/stderr line-by-line back to the UI, parse progress,
support cancellation) lands in Phase 1.
"""

from __future__ import annotations

from collections.abc import Callable


class CommandRunner:
    """Runs a yt-dlp command as a subprocess and streams its output.

    The interface is defined now so the UI can hold a reference and wire up
    Run/Stop buttons in later phases. Bodies raise ``NotImplementedError``
    until Phase 1 fills them in.
    """

    def __init__(self, on_output: Callable[[str], None] | None = None) -> None:
        """Create a runner.

        Args:
            on_output: Optional callback invoked with each line of output as it
                streams in. Wired to the log console / progress parser in Phase 1.
        """
        self._on_output = on_output

    def run(self, args: list[str]) -> None:
        """Launch ``yt-dlp`` with ``args`` and stream its output.

        Args:
            args: The yt-dlp argument list (URLs and flags), NOT including the
                ``yt-dlp`` executable name itself.

        Raises:
            NotImplementedError: Always, in Phase 0. Implemented in Phase 1.
        """
        raise NotImplementedError("CommandRunner.run is implemented in Phase 1.")

    def stop(self) -> None:
        """Terminate the running subprocess, if any.

        Raises:
            NotImplementedError: Always, in Phase 0. Implemented in Phase 1.
        """
        raise NotImplementedError("CommandRunner.stop is implemented in Phase 1.")
