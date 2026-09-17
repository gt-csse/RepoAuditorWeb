"""Contains the LogSink object."""

from typing import override, TYPE_CHECKING

from dbrownell_Common.Streams.TextWriter import TextWriter

if TYPE_CHECKING:
    from textual.app import App
    from textual.widgets import RichLog


# ----------------------------------------------------------------------
class LogSink(TextWriter):
    """Stream that displays everything written to it within the application's log.

    DoneManager writes synchronously from the thread performing the execution, but a widget may only
    be touched by the thread that owns it, so each write is posted to that thread.
    """

    # ----------------------------------------------------------------------
    def __init__(self, app: App, log: RichLog) -> None:
        self._app = app
        self._log = log

        # DoneManager writes content that is not line-delimited (it indents as it goes), so content
        # is accumulated until a line is complete rather than written once per call.
        self._pending = ""

    # ----------------------------------------------------------------------
    @override
    def write(self, content: str) -> int:
        """Display content written by DoneManager."""

        for index, part in enumerate(content.split("\n")):
            # Every part after the first was preceded by a newline, which completes whatever has
            # been accumulated so far.
            if index > 0:
                self._WritePending()

            self._pending += part

        return len(content)

    # ----------------------------------------------------------------------
    @override
    def flush(self) -> None:
        """Display content that is not yet a complete line."""

        self._WritePending()

    # ----------------------------------------------------------------------
    @override
    def isatty(self) -> bool:
        """Indicate that the stream is not a terminal so that colors are not emitted."""

        return False

    # ----------------------------------------------------------------------
    @override
    def close(self) -> None:
        """Display whatever remains."""

        self.flush()

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def _WritePending(self) -> None:
        # DoneManager writes a line's text and the newline that ends it as separate calls, so an
        # empty accumulation is the second of that pair rather than a blank line of its own.
        if not self._pending:
            return

        line = self._pending
        self._pending = ""

        self._app.call_from_thread(self._log.write, line)
