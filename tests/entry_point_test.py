import io

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
def test_Version():
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"{__version__}\n"


# ----------------------------------------------------------------------
def test_Help():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    assert {"--port", "--token", "--verbose", "--debug", "--version"} <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_DynamicModuleOptionsAppearInHelp():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    assert {
        "--GitHub-include",
        "--GitHub-three",
        "--GitHub-four",
        "--CommunityStandards-include",
        "--CommunityStandards-one",
        "--CommunityStandards-two",
        "--ScientificSoftware-include",
        "--ScientificSoftware-five",
        "--ScientificSoftware-six",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_NoArguments():
    result = CliRunner().invoke(app, [])

    assert result.exit_code == 0, result.output


# ----------------------------------------------------------------------
def test_DynamicOptionValueIsResolved():
    result, output = _InvokeAndCapture(["--GitHub-three", "50"])

    assert result.exit_code == 0, output
    assert "'three': 50" in output


# ----------------------------------------------------------------------
def test_DefaultsAreResolved():
    result, output = _InvokeAndCapture([])

    assert result.exit_code == 0, output

    # Module-level parameters are filed under a None requirement name.
    for expected in [
        "'GitHub': {None: {'include': False, 'three': 30, 'four': '4'}}",
        "'CommunityStandards': {None: {'include': False, 'one': 10, 'two': '2'}}",
        "'ScientificSoftware': {None: {'include': False, 'five': 50, 'six': False}}",
    ]:
        assert expected in output


# ----------------------------------------------------------------------
def test_ModuleIncludeOptionIsResolved():
    result, output = _InvokeAndCapture(["--GitHub-include"])

    assert result.exit_code == 0, output
    assert "'GitHub': {None: {'include': True, 'three': 30, 'four': '4'}}" in output


# ----------------------------------------------------------------------
def test_InvalidPort():
    result = CliRunner().invoke(app, ["--port", "80"])

    assert result.exit_code != 0


# ----------------------------------------------------------------------
def test_Verbose():
    result = CliRunner().invoke(app, ["--verbose"])

    assert result.exit_code == 0, result.output
