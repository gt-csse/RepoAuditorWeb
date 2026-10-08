import json
import textwrap

from collections.abc import Mapping
from unittest import mock

import git
import pytest
import typer

from typer.testing import CliRunner, Result

from RepoAuditorWeb import __version__, APP_NAME
from RepoAuditorWeb.__main__ import app


# ----------------------------------------------------------------------
def _GetOptionNames(typer_app) -> set[str]:
    # rich renders help text against the ambient terminal, truncating long option names and
    # splitting short ones across color escapes, so the registered names are asserted instead.
    return {decl for param in typer.main.get_command(typer_app).params for decl in param.opts}


# ----------------------------------------------------------------------
def _InvokeAndCapture(args: list[str]) -> tuple[Result, str]:
    result = CliRunner().invoke(app, args)

    return result, result.output


# ----------------------------------------------------------------------
# Modules are not included by default, so no network calls are made. The console experience
# is requested explicitly because the default experience opens a window and does not return until it
# is closed.
_SKIP_NETWORK = ["--experience", "console"]


# ----------------------------------------------------------------------
def test_Version():
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output == f"{APP_NAME} v{__version__}\n"


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
def test_ConfigIsTheFirstOption():
    assert typer.main.get_command(app).params[0].opts == ["--config"]


# ----------------------------------------------------------------------
def test_DynamicModuleOptionsAppearInHelp():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output

    assert {
        "--GitHub-include",
        "--GitHub-url",
        "--GitHub-pat",
        "--GitHub-branch",
        "--CommunityStandards-include",
        "--CommunityStandards-url",
        "--CommunityStandards-pat",
        "--CommunityStandards-branch",
        "--ScientificSoftware-include",
        "--ScientificSoftware-url",
        "--ScientificSoftware-pat",
        "--ScientificSoftware-branch",
        "--JOSS-include",
        "--JOSS-url",
        "--JOSS-pat",
        "--JOSS-branch",
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
        "--GitHub-WebCommitSignoff-require",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
def test_NoArguments():
    result, _ = _InvokeAndCapture(_SKIP_NETWORK)

    assert result.exit_code == 0, result.output


# ----------------------------------------------------------------------
def test_ModulesAreExecuted():
    result, output = _InvokeAndCapture(_SKIP_NETWORK)

    assert result.exit_code == 0, output

    for expected in [
        "Executing module 'GitHub' (1 of 4)...",
        "Executing module 'CommunityStandards' (2 of 4)...",
        "Executing module 'JOSS' (3 of 4)...",
        "Executing module 'ScientificSoftware' (4 of 4)...",
    ]:
        assert expected in output


# ----------------------------------------------------------------------
# Modules that are not explicitly included are reported as skipped.
def test_ModulesAreSkipped():
    _, output = _InvokeAndCapture(_SKIP_NETWORK)

    assert output.count("SKIPPED.") == 4


# ----------------------------------------------------------------------
# A local repository is cloned so that the included module executes without network access.
def test_ModuleIncludeOptionIsResolved(tmp_path):
    source_repo = git.Repo.init(tmp_path)
    (tmp_path / "CITATION.cff").write_text("content", encoding="utf-8")
    source_repo.index.add(["CITATION.cff"])
    source_repo.index.commit("Initial commit", author=git.Actor("Me", "me@example.com"))

    result, output = _InvokeAndCapture(
        [*_SKIP_NETWORK, "--ScientificSoftware-include", "--ScientificSoftware-url", tmp_path.as_uri()],
    )

    assert result.exit_code == 0, output
    assert output.count("SKIPPED.") == 3


# ----------------------------------------------------------------------
# The GitHub module requires a url, so it fails when it is executed without one.
def test_ErrorGitHubModuleWithoutUrl():
    result, output = _InvokeAndCapture(["--GitHub-include", "--experience", "console"])

    assert result.exit_code != 0
    assert "'url' is a required argument for this module." in output


# ----------------------------------------------------------------------
def test_InvalidPort():
    result = CliRunner().invoke(app, ["--port", "80"])

    assert result.exit_code != 0


# ----------------------------------------------------------------------
def test_Verbose():
    result, output = _InvokeAndCapture([*_SKIP_NETWORK, "--verbose"])

    assert result.exit_code == 0, output


# ----------------------------------------------------------------------
class TestExperience:
    # ----------------------------------------------------------------------
    def test_SummaryIsWritten(self):
        result, output = _InvokeAndCapture(_SKIP_NETWORK)

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
        result, output = _InvokeAndCapture([*_SKIP_NETWORK, "--experience", "console"])

        assert result.exit_code == 0, output
        assert "Skipped:" in output

    # ----------------------------------------------------------------------
    def test_ConsoleIsCaseInsensitive(self):
        result, output = _InvokeAndCapture([*_SKIP_NETWORK, "--experience", "CONSOLE"])

        assert result.exit_code == 0, output
        assert "Skipped:" in output

    # ----------------------------------------------------------------------
    # The web experience is the default, and it does not return until the window it opens is closed,
    # so it is replaced by a double rather than being invoked.
    def test_WebIsTheDefault(self):
        with mock.patch("RepoAuditorWeb.__main__.ExecuteWebExperience") as experience_mock:
            result, output = _InvokeAndCapture([])

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

    # ----------------------------------------------------------------------
    def test_Web(self):
        with mock.patch("RepoAuditorWeb.__main__.ExecuteWebExperience") as experience_mock:
            result, output = _InvokeAndCapture(["--experience", "web"])

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

    # ----------------------------------------------------------------------
    # The TUI experience takes over the terminal and does not return until the user closes it, so it
    # is replaced by a double rather than being invoked.
    def test_Tui(self):
        with mock.patch("RepoAuditorWeb.__main__.ExecuteTuiExperience") as experience_mock:
            result, output = _InvokeAndCapture(["--experience", "tui"])

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

    # ----------------------------------------------------------------------
    def test_Json(self):
        result = CliRunner().invoke(app, ["--experience", "json"])

        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == {
            "schema_version": 1,
            "summary": {
                "skipped": 0,
                "does_not_apply": 0,
                "success": 0,
                "warning": 0,
                "error": 0,
                "total": 0,
            },
            "results": [],
        }

    # ----------------------------------------------------------------------
    # Everything that DoneManager produces is written to stderr so that the document written to
    # stdout can be redirected to a file or piped to another process as-is.
    def test_JsonProgressIsWrittenToStderr(self):
        result = CliRunner().invoke(app, ["--experience", "json"])

        assert result.exit_code == 0, result.output
        assert "Executing module 'GitHub' (1 of 4)..." in result.stderr
        assert "Executing module" not in result.stdout

    # ----------------------------------------------------------------------
    # The status output and the document are written to different streams, so the status output
    # ends with a blank line to separate them when both are displayed together.
    def test_JsonStatusOutputEndsWithASeparator(self):
        result = CliRunner().invoke(app, ["--experience", "json"])

        assert result.exit_code == 0, result.output

        lines = result.stderr.splitlines()

        assert lines[-1] == ""
        assert lines[-2] == ""
        assert lines[-3].startswith("Results: DONE!")

    # ----------------------------------------------------------------------
    # The console experience writes everything to one stream, so it adds no separator.
    def test_ConsoleStatusOutputHasNoSeparator(self):
        result = CliRunner().invoke(app, _SKIP_NETWORK)

        assert result.exit_code == 0, result.output

        lines = result.stdout.splitlines()

        assert lines[-1] == ""
        assert lines[-2].startswith("Results: DONE!")

    # ----------------------------------------------------------------------
    def test_InvalidExperience(self):
        result = CliRunner().invoke(app, [*_SKIP_NETWORK, "--experience", "invalid"])

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
        kwargs = self._InvokeAndCaptureKwargs(_SKIP_NETWORK)

        assert kwargs["display_resolution"] is True
        assert kwargs["display_rationale"] is True

    # ----------------------------------------------------------------------
    def test_NoResolution(self):
        kwargs = self._InvokeAndCaptureKwargs([*_SKIP_NETWORK, "--no-resolution"])

        assert kwargs["display_resolution"] is False
        assert kwargs["display_rationale"] is True

    # ----------------------------------------------------------------------
    def test_NoRationale(self):
        kwargs = self._InvokeAndCaptureKwargs([*_SKIP_NETWORK, "--no-rationale"])

        assert kwargs["display_resolution"] is True
        assert kwargs["display_rationale"] is False

    # ----------------------------------------------------------------------
    def test_PortAndTokenAreForwarded(self):
        kwargs = self._InvokeAndCaptureKwargs([*_SKIP_NETWORK, "--port", "8080", "--token", "my_token"])

        assert kwargs["port"] == 8080
        assert kwargs["token"] == "my_token"

    # ----------------------------------------------------------------------
    def test_NoExecuteByDefault(self):
        assert self._InvokeAndCaptureKwargs(_SKIP_NETWORK)["execute"] is False

    # ----------------------------------------------------------------------
    def test_Execute(self):
        assert self._InvokeAndCaptureKwargs([*_SKIP_NETWORK, "--execute"])["execute"] is True


# ----------------------------------------------------------------------
class TestCommonOptions:
    # ----------------------------------------------------------------------
    # The experience is replaced by a double so that the modules (which access the network) are not
    # executed; the arguments it receives are asserted instead.
    @staticmethod
    def _InvokeAndCaptureArguments(
        args: list[str],
        env: dict[str, str | None] | None = None,
    ) -> dict[str, dict[str | None, dict[str, object]]]:
        # The environment is cleared so that values set on the host do not influence the results.
        env = {
            "REPO_AUDITOR_WEB_GITHUB_URL": None,
            "REPO_AUDITOR_WEB_GITHUB_PAT": None,
            "REPO_AUDITOR_WEB_GITHUB_BRANCH": None,
            **(env or {}),
        }

        with mock.patch("RepoAuditorWeb.__main__.ExecuteConsoleExperience") as experience_mock:
            result = CliRunner().invoke(app, [*args, "--experience", "console"], env=env)

        assert result.exit_code == 0, result.output
        assert experience_mock.call_count == 1

        return experience_mock.call_args.kwargs["arguments"]

    # ----------------------------------------------------------------------
    def test_InHelp(self):
        assert {"--url", "--pat", "--branch"} <= _GetOptionNames(app)

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("option", "parameter_name", "value"),
        [
            ("--url", "url", "https://github.com/gt-csse/RepoAuditorWeb"),
            ("--pat", "pat", "my_pat"),
            ("--branch", "branch", "my_branch"),
        ],
    )
    def test_ForwardedToModules(self, option, parameter_name, value):
        arguments = self._InvokeAndCaptureArguments([option, value])

        assert arguments["GitHub"][None][parameter_name] == value
        assert arguments["CommunityStandards"][None][parameter_name] == value
        assert arguments["ScientificSoftware"][None][parameter_name] == value

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("envvar", "parameter_name", "value"),
        [
            ("REPO_AUDITOR_WEB_GITHUB_URL", "url", "https://github.com/gt-csse/RepoAuditorWeb"),
            ("REPO_AUDITOR_WEB_GITHUB_PAT", "pat", "my_pat"),
            ("REPO_AUDITOR_WEB_GITHUB_BRANCH", "branch", "my_branch"),
        ],
    )
    def test_EnvironmentVariables(self, envvar, parameter_name, value):
        arguments = self._InvokeAndCaptureArguments([], env={envvar: value})

        assert arguments["GitHub"][None][parameter_name] == value
        assert arguments["CommunityStandards"][None][parameter_name] == value
        assert arguments["ScientificSoftware"][None][parameter_name] == value

    # ----------------------------------------------------------------------
    # Module-specific values are left untouched when the common option is not provided.
    def test_ModuleValuesPreservedWhenAbsent(self):
        arguments = self._InvokeAndCaptureArguments(
            [
                "--GitHub-url",
                "https://github.com/gt-csse/GitHubRepo",
                "--CommunityStandards-url",
                "https://github.com/gt-csse/CommunityStandardsRepo",
            ],
        )

        assert arguments["GitHub"][None]["url"] == "https://github.com/gt-csse/GitHubRepo"
        assert (
            arguments["CommunityStandards"][None]["url"]
            == "https://github.com/gt-csse/CommunityStandardsRepo"
        )

    # ----------------------------------------------------------------------
    # Module-specific values take precedence over the common option, which still applies to the
    # modules that were not given a specific value.
    @pytest.mark.parametrize(
        ("parameter_name", "value"),
        [
            ("url", "https://github.com/gt-csse/RepoAuditorWeb"),
            ("pat", "my_pat"),
            ("branch", "my_branch"),
        ],
    )
    def test_ModuleValuesTakePrecedence(self, parameter_name, value):
        arguments = self._InvokeAndCaptureArguments(
            [f"--{parameter_name}", value, f"--GitHub-{parameter_name}", "module_value"],
        )

        assert arguments["GitHub"][None][parameter_name] == "module_value"
        assert arguments["CommunityStandards"][None][parameter_name] == value

    # ----------------------------------------------------------------------
    # Config file keys are the python parameter names, which is how the dynamic module and
    # requirement parameters are registered with typer.
    def test_ConfigFile(self, tmp_path):
        config_filename = tmp_path / "config.yaml"
        config_filename.write_text(
            textwrap.dedent(
                """\
                url: https://github.com/gt-csse/RepoAuditorWeb
                GitHub_include: true
                GitHub_branch: config_branch
                GitHub_Description_value: empty
                """,
            ),
            encoding="utf-8",
        )

        arguments = self._InvokeAndCaptureArguments(
            ["--config", str(config_filename), "--GitHub-branch", "cli_branch"],
        )

        assert arguments["GitHub"][None]["include"] is True
        assert arguments["GitHub"][None]["url"] == "https://github.com/gt-csse/RepoAuditorWeb"
        assert arguments["GitHub"][None]["branch"] == "cli_branch"
        assert arguments["GitHub"]["Description"]["value"] == "empty"
        assert arguments["CommunityStandards"][None]["include"] is False
        assert arguments["CommunityStandards"][None]["url"] == "https://github.com/gt-csse/RepoAuditorWeb"

    # ----------------------------------------------------------------------
    def test_ModuleValuesTakePrecedenceOverEnvironmentVariables(self):
        arguments = self._InvokeAndCaptureArguments(
            ["--CommunityStandards-branch", "module_branch"],
            env={"REPO_AUDITOR_WEB_GITHUB_BRANCH": "env_branch"},
        )

        assert arguments["GitHub"][None]["branch"] == "env_branch"
        assert arguments["CommunityStandards"][None]["branch"] == "module_branch"
