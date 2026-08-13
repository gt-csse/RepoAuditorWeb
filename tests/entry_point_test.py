import typer

from typer.testing import CliRunner

from RepoAuditorWeb import __version__
from RepoAuditorWeb.__main__ import app


# ----------------------------------------------------------------------
def _GetOptionNames(typer_app) -> set[str]:
    # rich renders help text against the ambient terminal, truncating long option names and
    # splitting short ones across color escapes, so the registered names are asserted instead.
    return {decl for param in typer.main.get_command(typer_app).params for decl in param.opts}


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
        "--GitHub-three",
        "--GitHub-four",
        "--CommunityStandards-one",
        "--CommunityStandards-two",
        "--ScientificSoftware-five",
        "--ScientificSoftware-six",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_NoArguments():
    result = CliRunner().invoke(app, [])

    assert result.exit_code == 0, result.output


# ----------------------------------------------------------------------
def test_DynamicOptionValueIsResolved():
    result = CliRunner().invoke(app, ["--GitHub-three", "50"])

    assert result.exit_code == 0, result.output
    assert "'three': 50" in result.output


# ----------------------------------------------------------------------
def test_DefaultsAreResolved():
    result = CliRunner().invoke(app, [])

    assert result.exit_code == 0, result.output

    for expected in [
        "'GitHub': {'three': 30, 'four': '4'}",
        "'CommunityStandards': {'one': 10, 'two': '2'}",
        "'ScientificSoftware': {'five': 50, 'six': False}",
    ]:
        assert expected in result.output


# ----------------------------------------------------------------------
def test_InvalidPort():
    result = CliRunner().invoke(app, ["--port", "80"])

    assert result.exit_code != 0


# ----------------------------------------------------------------------
def test_Verbose():
    result = CliRunner().invoke(app, ["--verbose"])

    assert result.exit_code == 0, result.output
