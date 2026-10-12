"""Contains the StreamSink object."""

import threading

from typing import override, TYPE_CHECKING

from dbrownell_Common.Streams.TextWriter import TextWriter

if TYPE_CHECKING:
    from collections.abc import Iterator


# ----------------------------------------------------------------------
class StreamSink(TextWriter):
    """Stream that queues everything written to it so that another thread can consume it.

    DoneManager writes synchronously from the thread performing the execution, but the content must
    be delivered to a client on the thread servicing its request. A condition decouples the two
    without the consumer polling for changes.

    Events are retained rather than consumed so that every subscriber, including one that reconnects
    or arrives after the run completed, receives all of them and observes the end of the stream.
    """

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        self._events: list[tuple[str, dict[str, object]]] = []
        self._is_closed = False
        self._condition = threading.Condition()

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

        with self._condition:
            self._events.append((event_type, data))
            self._condition.notify_all()

    # ----------------------------------------------------------------------
    def Close(self) -> None:
        """Indicate that no further content will be written."""

        with self._condition:
            self._is_closed = True
            self._condition.notify_all()

    # ----------------------------------------------------------------------
    def Enumerate(self) -> Iterator[tuple[str, dict[str, object]]]:
        """Yield every event from the first until the sink is closed, blocking while none are new."""

        index = 0

        while True:
            with self._condition:
                while index == len(self._events) and not self._is_closed:
                    self._condition.wait()

                events = self._events[index:]
                is_closed = self._is_closed

            # Events are yielded outside of the lock so that a slow consumer does not block writes.
            yield from events

            if is_closed:
                break

            index += len(events)
