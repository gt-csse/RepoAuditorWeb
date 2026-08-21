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
# The GitHub module is skipped so that no network calls are made.
_SKIP_GITHUB = ["--GitHub-skip"]


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
    result, output = _InvokeAndCapture([])

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
