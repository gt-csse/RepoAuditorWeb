from unittest import mock

from RepoAuditorWeb.tui_experience_impl.log_sink import LogSink


# ----------------------------------------------------------------------
def _CreateSink() -> tuple[LogSink, mock.MagicMock]:
    # A widget may only be touched by the thread that owns it, so the write is posted to that thread
    # rather than performed directly; the double invokes it so that what was written is observable.
    app = mock.MagicMock()
    app.call_from_thread.side_effect = lambda func, *args: func(*args)

    log = mock.MagicMock()

    return LogSink(app, log), log


# ----------------------------------------------------------------------
def _CreateLines(log: mock.MagicMock) -> list[str]:
    return [call.args[0] for call in log.write.call_args_list]


# ----------------------------------------------------------------------
class TestWrite:
    # ----------------------------------------------------------------------
    def test_CompleteLineIsDisplayed(self):
        sink, log = _CreateSink()

        assert sink.write("my line\n") == len("my line\n")
        assert _CreateLines(log) == ["my line"]

    # ----------------------------------------------------------------------
    def test_MultipleLines(self):
        sink, log = _CreateSink()

        sink.write("one\ntwo\n")

        assert _CreateLines(log) == ["one", "two"]

    # ----------------------------------------------------------------------
    # DoneManager writes content that is not line-delimited, so content is held until the line it
    # belongs to is complete.
    def test_IncompleteLineIsHeld(self):
        sink, log = _CreateSink()

        sink.write("my ")

        assert _CreateLines(log) == []

    # ----------------------------------------------------------------------
    def test_HeldContentIsDisplayedOnceTheLineIsComplete(self):
        sink, log = _CreateSink()

        sink.write("my ")
        sink.write("line\n")

        assert _CreateLines(log) == ["my line"]

    # ----------------------------------------------------------------------
    def test_ContentAfterTheLastNewlineIsHeld(self):
        sink, log = _CreateSink()

        sink.write("one\ntwo")

        assert _CreateLines(log) == ["one"]

    # ----------------------------------------------------------------------
    # DoneManager writes a line's text and the newline that ends it as separate calls, so a
    # newline on its own ends the line already written rather than displaying a blank one.
    def test_NewlineAloneDisplaysNothing(self):
        sink, log = _CreateSink()

        sink.write("\n")

        assert _CreateLines(log) == []

    # ----------------------------------------------------------------------
    # The text of a status line and the result DoneManager appends to it arrive as separate
    # calls with no newline between them, so they are displayed as one line.
    def test_ContentWrittenAcrossCallsIsOneLine(self):
        sink, log = _CreateSink()

        sink.write("Extracting data...")
        sink.write("DONE!")
        sink.write("\n")

        assert _CreateLines(log) == ["Extracting data...DONE!"]

    # ----------------------------------------------------------------------
    # The status output of a run contains no blank lines of its own.
    def test_ConsecutiveNewlinesDisplayNothing(self):
        sink, log = _CreateSink()

        sink.write("my line\n")
        sink.write("\n")
        sink.write("\n")

        assert _CreateLines(log) == ["my line"]

    # ----------------------------------------------------------------------
    def test_NothingWritten(self):
        sink, log = _CreateSink()

        assert sink.write("") == 0
        assert _CreateLines(log) == []


# ----------------------------------------------------------------------
class TestFlush:
    # ----------------------------------------------------------------------
    def test_HeldContentIsDisplayed(self):
        sink, log = _CreateSink()

        sink.write("my line")
        sink.flush()

        assert _CreateLines(log) == ["my line"]

    # ----------------------------------------------------------------------
    def test_HeldContentIsDisplayedOnce(self):
        sink, log = _CreateSink()

        sink.write("my line")
        sink.flush()
        sink.flush()

        assert _CreateLines(log) == ["my line"]

    # ----------------------------------------------------------------------
    def test_NothingHeld(self):
        sink, log = _CreateSink()

        sink.flush()

        assert _CreateLines(log) == []


# ----------------------------------------------------------------------
class TestStreamInterface:
    # ----------------------------------------------------------------------
    # DoneManager emits colors only for a stream that is a terminal.
    def test_IsNotATerminal(self):
        assert _CreateSink()[0].isatty() is False

    # ----------------------------------------------------------------------
    def test_CloseDisplaysHeldContent(self):
        sink, log = _CreateSink()

        sink.write("my line")
        sink.close()

        assert _CreateLines(log) == ["my line"]
