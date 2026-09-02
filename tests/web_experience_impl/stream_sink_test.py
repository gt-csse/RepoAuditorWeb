import threading

from RepoAuditorWeb.web_experience_impl.stream_sink import StreamSink


# ----------------------------------------------------------------------
def _Drain(sink: StreamSink) -> list[tuple[str, dict[str, object]]]:
    sink.Close()

    return list(sink.Enumerate())


# ----------------------------------------------------------------------
class TestWrite:
    # ----------------------------------------------------------------------
    def test_ContentIsQueued(self):
        sink = StreamSink()
        sink.write("Hello")

        assert _Drain(sink) == [("output", {"content": "Hello"})]

    # ----------------------------------------------------------------------
    # DoneManager expects the number of characters written.
    def test_ReturnsTheLength(self):
        assert StreamSink().write("Hello") == 5

    # ----------------------------------------------------------------------
    def test_EmptyContentIsNotQueued(self):
        sink = StreamSink()

        assert sink.write("") == 0
        assert _Drain(sink) == []

    # ----------------------------------------------------------------------
    def test_WritesAreQueuedInOrder(self):
        sink = StreamSink()
        sink.write("One")
        sink.write("Two")

        assert _Drain(sink) == [
            ("output", {"content": "One"}),
            ("output", {"content": "Two"}),
        ]


# ----------------------------------------------------------------------
class TestStreamInterface:
    # ----------------------------------------------------------------------
    def test_Flush(self):
        sink = StreamSink()
        sink.flush()

        assert _Drain(sink) == []

    # ----------------------------------------------------------------------
    # Colors are not emitted because the consumer displays the content as text.
    def test_IsNotATty(self):
        assert StreamSink().isatty() is False

    # ----------------------------------------------------------------------
    # Closing the stream terminates the enumeration, as nothing further can be written.
    def test_Close(self):
        sink = StreamSink()
        sink.write("Hello")
        sink.close()

        assert list(sink.Enumerate()) == [("output", {"content": "Hello"})]


# ----------------------------------------------------------------------
class TestSend:
    # ----------------------------------------------------------------------
    def test_EventIsQueued(self):
        sink = StreamSink()
        sink.Send("results", {"html": "<div></div>"})

        assert _Drain(sink) == [("results", {"html": "<div></div>"})]

    # ----------------------------------------------------------------------
    def test_EventsAreInterleavedWithWrites(self):
        sink = StreamSink()
        sink.write("One")
        sink.Send("error", {"message": "Two"})

        assert _Drain(sink) == [
            ("output", {"content": "One"}),
            ("error", {"message": "Two"}),
        ]


# ----------------------------------------------------------------------
class TestEnumerate:
    # ----------------------------------------------------------------------
    def test_EmptyOnceClosed(self):
        assert _Drain(StreamSink()) == []

    # ----------------------------------------------------------------------
    # Nothing is queued after the sink is closed, so a second enumeration yields nothing rather than
    # replaying what the first one consumed.
    def test_EnumerationConsumes(self):
        sink = StreamSink()
        sink.write("Hello")

        assert _Drain(sink) == [("output", {"content": "Hello"})]

        sink.Close()
        assert list(sink.Enumerate()) == []

    # ----------------------------------------------------------------------
    # The queue exists so that the consumer receives content as the producer writes it rather than
    # polling for changes.
    def test_BlocksUntilContentIsAvailable(self):
        sink = StreamSink()
        received: list[tuple[str, dict[str, object]]] = []
        first_received = threading.Event()

        # ----------------------------------------------------------------------
        def Consume() -> None:
            for item in sink.Enumerate():
                received.append(item)
                first_received.set()

        # ----------------------------------------------------------------------

        thread = threading.Thread(target=Consume, daemon=True)
        thread.start()

        sink.write("One")

        assert first_received.wait(timeout=5)

        sink.write("Two")
        sink.Close()

        thread.join(timeout=5)
        assert not thread.is_alive()

        assert received == [
            ("output", {"content": "One"}),
            ("output", {"content": "Two"}),
        ]
