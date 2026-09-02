"""Contains the StreamSink object."""

import queue

from typing import override, TYPE_CHECKING

from dbrownell_Common.Streams.TextWriter import TextWriter

if TYPE_CHECKING:
    from collections.abc import Iterator


# ----------------------------------------------------------------------
class StreamSink(TextWriter):
    """Stream that queues everything written to it so that another thread can consume it.

    DoneManager writes synchronously from the thread performing the execution, but the content must
    be delivered to a client on the thread servicing its request. A queue decouples the two without
    the consumer polling for changes.
    """

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        # Items are (event type, data); None terminates the enumeration.
        self._queue: queue.Queue[tuple[str, dict[str, object]] | None] = queue.Queue()

    # ----------------------------------------------------------------------
    @override
    def write(self, content: str) -> int:
        """Queue content written by DoneManager."""

        if content:
            self.Send("output", {"content": content})

        return len(content)

    # ----------------------------------------------------------------------
    @override
    def flush(self) -> None:
        """Satisfy the stream interface expected by DoneManager."""

    # ----------------------------------------------------------------------
    @override
    def isatty(self) -> bool:
        """Indicate that the stream is not a terminal so that colors are not emitted."""

        return False

    # ----------------------------------------------------------------------
    @override
    def close(self) -> None:
        """Satisfy the stream interface expected by DoneManager."""

        self.Close()

    # ----------------------------------------------------------------------
    def Send(self, event_type: str, data: dict[str, object]) -> None:
        """Queue an event that did not originate from a write."""

        self._queue.put((event_type, data))

    # ----------------------------------------------------------------------
    def Close(self) -> None:
        """Indicate that no further content will be written."""

        self._queue.put(None)

    # ----------------------------------------------------------------------
    def Enumerate(self) -> Iterator[tuple[str, dict[str, object]]]:
        """Yield queued events until the sink is closed, blocking while it is empty."""

        while True:
            item = self._queue.get()
            if item is None:
                break

            yield item
