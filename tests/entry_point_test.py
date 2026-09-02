import io

from collections.abc import Mapping
from unittest import mock

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager
from typer.testing import CliRunner, Result

from RepoAuditorWeb import __version__
from RepoAuditorWeb.__main__ import app


# ----------------------------------------------------------------------
def _GetOptionNames(typer_app) -> set[str]:
    # rich renders help text against the ambient terminal, truncating long option names and
    # splitting short ones across color escapes, so the registered names are asserted instead.
    return {decl for param in typer.main.get_command(typer_app).params for decl in param.opts}


# ----------------------------------------------------------------------
def _InvokeAndCapture(args: list[str]) -> tuple[Result, str]:
    # DoneManager.CreateCommandLine binds sys.stdout as a default argument value when
    # dbrownell_Common is imported, so its writes bypass both CliRunner's captured stream and
    # pytest's capture fixtures. Supplying the stream explicitly is the only way to observe them.
    sink = io.StringIO()
    original = DoneManager.CreateCommandLine

    def Patched(stream=sink, **kwargs):
        return original(stream, **kwargs)

    with mock.patch.object(DoneManager, "CreateCommandLine", Patched):
        result = CliRunner().invoke(app, args)

    return result, sink.getvalue()


# ----------------------------------------------------------------------
# The GitHub module is skipped so that no network calls are made. The console experience is
# requested explicitly because the default experience opens a window and does not return until it
# is closed.
_SKIP_GITHUB = ["--GitHub-skip", "--experience", "console"]


# ----------------------------------------------------------------------
def test_Version():
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"{__version__}\n"


# ----------------------------------------------------------------------
def test_Help():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    assert {
        "--port",
        "--token",
        "--experience",
        "--execute",
        "--no-resolution",
        "--no-rationale",
        "--verbose",
        "--debug",
        "--version",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_DynamicModuleOptionsAppearInHelp():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    assert {
        "--GitHub-skip",
        "--GitHub-url",
        "--GitHub-pat",
        "--GitHub-branch",
        "--CommunityStandards-include",
        "--CommunityStandards-one",
        "--CommunityStandards-two",
        "--ScientificSoftware-include",
        "--ScientificSoftware-five",
        "--ScientificSoftware-six",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_DynamicRequirementOptionsAppearInHelp():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    assert {
        "--GitHub-Description-skip",
        "--GitHub-Description-value",
        "--GitHub-License-skip",
        "--GitHub-License-value",
        "--GitHub-Template-skip",
        "--GitHub-Template-require",
        "--GitHub-WebCommitSignoff-skip",
        "--GitHub-WebCommitSignoff-no",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_NoArguments():
    result, _ = _InvokeAndCapture(_SKIP_GITHUB)

    assert result.exit_code == 0, result.output


# ----------------------------------------------------------------------
def test_ModulesAreExecuted():
    result, output = _InvokeAndCapture(_SKIP_GITHUB)

    assert result.exit_code == 0, output

    for expected in [
        "Executing module 'GitHub' (1 of 3)...",
        "Executing module 'CommunityStandards' (2 of 3)...",
        "Executing module 'ScientificSoftware' (3 of 3)...",
    ]:
        assert expected in output


# ----------------------------------------------------------------------
# Modules that are not explicitly included are reported as skipped.
def test_ModulesAreSkipped():
    _, output = _InvokeAndCapture(_SKIP_GITHUB)

    assert output.count("SKIPPED.") == 3


# ----------------------------------------------------------------------
def test_ModuleIncludeOptionIsResolved():
    result, output = _InvokeAndCapture([*_SKIP_GITHUB, "--CommunityStandards-include"])

    assert result.exit_code == 0, output
    assert output.count("SKIPPED.") == 2


# ----------------------------------------------------------------------
# The GitHub module requires a url, so it fails when it is executed without one.
def test_ErrorGitHubModuleWithoutUrl():
    result, output = _InvokeAndCapture(["--experience", "console"])

    assert result.exit_code != 0
    assert "'url' is required argument for this module." in output


# ----------------------------------------------------------------------
def test_InvalidPort():
    result = CliRunner().invoke(app, ["--port", "80"])

    assert result.exit_code != 0


# ----------------------------------------------------------------------
def test_Verbose():
    result, output = _InvokeAndCapture([*_SKIP_GITHUB, "--verbose"])

    assert result.exit_code == 0, output


# ----------------------------------------------------------------------
class TestExperience:
    # ----------------------------------------------------------------------
    def test_SummaryIsWritten(self):
        result, output = _InvokeAndCapture(_SKIP_GITHUB)

        assert result.exit_code == 0, output

        for expected in [
            "Skipped:",
            "Does Not Apply:",
            "Success:",
            "Warning:",
            "Error:",
        ]:
            assert expected in output

    # ----------------------------------------------------------------------
    def test_Console(self):
        result, output = _InvokeAndCapture([*_SKIP_GITHUB, "--experience", "console"])

        assert result.exit_code == 0, output
        assert "Skipped:" in output

    # ----------------------------------------------------------------------
    def test_ConsoleIsCaseInsensitive(self):
        result, output = _InvokeAndCapture([*_SKIP_GITHUB, "--experience", "CONSOLE"])

        assert result.exit_code == 0, output
        assert "Skipped:" in output

    # ----------------------------------------------------------------------
    # The web experience is the default, and it does not return until the window it opens is closed,
    # so it is replaced by a double rather than being invoked.
    def test_WebIsTheDefault(self):
        with mock.patch("RepoAuditorWeb.__main__.ExecuteWebExperience") as experience_mock:
            result, output = _InvokeAndCapture(["--GitHub-skip"])

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

    # ----------------------------------------------------------------------
    def test_Web(self):
        with mock.patch("RepoAuditorWeb.__main__.ExecuteWebExperience") as experience_mock:
            result, output = _InvokeAndCapture(["--GitHub-skip", "--experience", "web"])

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

    # ----------------------------------------------------------------------
    def test_InvalidExperience(self):
        result = CliRunner().invoke(app, [*_SKIP_GITHUB, "--experience", "invalid"])

        assert result.exit_code != 0


# ----------------------------------------------------------------------
class TestForwardedOptions:
    # ----------------------------------------------------------------------
    # Some options are transformed before being forwarded (the display flags are inverted) and
    # others are acted upon by the experience itself, so the values that the experience receives are
    # asserted rather than the output it would produce.
    @staticmethod
    def _InvokeAndCaptureKwargs(args: list[str]) -> Mapping[str, object]:
        with mock.patch("RepoAuditorWeb.__main__.ExecuteConsoleExperience") as experience_mock:
            result, output = _InvokeAndCapture(args)

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

        return experience_mock.call_args.kwargs

    # ----------------------------------------------------------------------
    def test_DisplayedByDefault(self):
        kwargs = self._InvokeAndCaptureKwargs(_SKIP_GITHUB)

        assert kwargs["display_resolution"] is True
        assert kwargs["display_rationale"] is True

    # ----------------------------------------------------------------------
    def test_NoResolution(self):
        kwargs = self._InvokeAndCaptureKwargs([*_SKIP_GITHUB, "--no-resolution"])

        assert kwargs["display_resolution"] is False
        assert kwargs["display_rationale"] is True

    # ----------------------------------------------------------------------
    def test_NoRationale(self):
        kwargs = self._InvokeAndCaptureKwargs([*_SKIP_GITHUB, "--no-rationale"])

        assert kwargs["display_resolution"] is True
        assert kwargs["display_rationale"] is False

    # ----------------------------------------------------------------------
    def test_PortAndTokenAreForwarded(self):
        kwargs = self._InvokeAndCaptureKwargs([*_SKIP_GITHUB, "--port", "8080", "--token", "my_token"])

        assert kwargs["port"] == 8080
        assert kwargs["token"] == "my_token"

    # ----------------------------------------------------------------------
    def test_NoExecuteByDefault(self):
        assert self._InvokeAndCaptureKwargs(_SKIP_GITHUB)["execute"] is False

    # ----------------------------------------------------------------------
    def test_Execute(self):
        assert self._InvokeAndCaptureKwargs([*_SKIP_GITHUB, "--execute"])["execute"] is True
