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
        "--include-archived",
        "--include-forked",
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
        "--CommunityStandards-include",
        "--ScientificSoftware-include",
        "--JOSS-include",
    } <= _GetOptionNames(app)


# ----------------------------------------------------------------------
# Every module operates on the common value, so a module-specific value is not accepted.
def test_ModuleOptionsForCommonOptionsAreNotAvailable():
    option_names = _GetOptionNames(app)

    for module_name in ["GitHub", "CommunityStandards", "ScientificSoftware", "JOSS"]:
        for parameter_name in ["url", "pat", "branch"]:
            assert f"--{module_name}-{parameter_name}" not in option_names


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
        [*_SKIP_NETWORK, "--ScientificSoftware-include", "--url", tmp_path.as_uri()],
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
    def test_Json(self):
        result = CliRunner().invoke(app, ["--experience", "json"])

        assert result.exit_code == 0, result.output

        document = json.loads(result.stdout)

        assert document["schema_version"] == 2
        assert document["error"] is None
        assert len(document["repositories"]) == 1

        repository = document["repositories"][0]

        assert repository["common_arguments"] == {"url": None, "pat": None, "branch": None}
        assert repository["error"] is None
        assert repository["summary"] == {
            "skipped": 0,
            "does_not_apply": 0,
            "success": 0,
            "warning": 0,
            "error": 0,
            "total": 0,
        }
        assert repository["results"] == []

    # ----------------------------------------------------------------------
    # Everything that DoneManager produces is written to stderr so that the document written to
    # stdout can be redirected to a file or piped to another process as-is.
    def test_JsonProgressIsWrittenToStderr(self):
        result = CliRunner().invoke(app, ["--experience", "json"])

        assert result.exit_code == 0, result.output
        assert "Executing module 'GitHub' (1 of 4)..." in result.stderr
        assert "Executing module" not in result.stdout

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
    ) -> tuple[dict[str, dict[str | None, dict[str, object]]], dict[str, object]]:
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

        kwargs = experience_mock.call_args.kwargs

        # A url without a wildcard is forwarded as a list of one repository.
        assert len(kwargs["urls"]) == 1

        return kwargs["arguments"], {"url": kwargs["urls"][0], **kwargs["common_arguments"]}

    # ----------------------------------------------------------------------
    def test_InHelp(self):
        assert {"--url", "--pat", "--branch"} <= _GetOptionNames(app)

    # ----------------------------------------------------------------------
    def test_NoneByDefault(self):
        _, common_arguments = self._InvokeAndCaptureArguments([])

        assert common_arguments == {"url": None, "pat": None, "branch": None}

    # ----------------------------------------------------------------------
    # Common values are applied to the modules when they are executed, so they are forwarded on their
    # own rather than as module arguments.
    @pytest.mark.parametrize(
        ("option", "parameter_name", "value"),
        [
            ("--url", "url", "https://github.com/gt-csse/RepoAuditorWeb"),
            ("--pat", "pat", "my_pat"),
            ("--branch", "branch", "my_branch"),
        ],
    )
    def test_ForwardedToExperience(self, option, parameter_name, value):
        arguments, common_arguments = self._InvokeAndCaptureArguments([option, value])

        assert common_arguments[parameter_name] == value

        for module_name in ["GitHub", "CommunityStandards", "ScientificSoftware", "JOSS"]:
            assert parameter_name not in arguments[module_name][None]

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
        _, common_arguments = self._InvokeAndCaptureArguments([], env={envvar: value})

        assert common_arguments[parameter_name] == value

    # ----------------------------------------------------------------------
    # Every module operates on the common value, so a module-specific value is rejected.
    @pytest.mark.parametrize("parameter_name", ["url", "pat", "branch"])
    def test_ErrorModuleValue(self, parameter_name):
        # The exception is asserted rather than the output, as rich splits option names across
        # color escapes when rendering against a terminal (which is forced on GitHub Actions).
        result = CliRunner().invoke(
            app,
            [*_SKIP_NETWORK, f"--GitHub-{parameter_name}", "module_value"],
            standalone_mode=False,
        )

        assert str(result.exception) == f"No such option: --GitHub-{parameter_name}"

    # ----------------------------------------------------------------------
    # Config file keys are the python parameter names, which is how the dynamic module and
    # requirement parameters are registered with typer.
    def test_ConfigFile(self, tmp_path):
        config_filename = tmp_path / "config.yaml"
        config_filename.write_text(
            textwrap.dedent(
                """\
                url: https://github.com/gt-csse/RepoAuditorWeb
                branch: config_branch
                GitHub_include: true
                GitHub_Description_value: empty
                """,
            ),
            encoding="utf-8",
        )

        arguments, common_arguments = self._InvokeAndCaptureArguments(
            ["--config", str(config_filename), "--branch", "cli_branch"],
        )

        assert common_arguments == {
            "url": "https://github.com/gt-csse/RepoAuditorWeb",
            "pat": None,
            "branch": "cli_branch",
        }
        assert arguments["GitHub"][None]["include"] is True
        assert arguments["GitHub"]["Description"]["value"] == "empty"
        assert arguments["CommunityStandards"][None]["include"] is False


# ----------------------------------------------------------------------
def _CreateRepositories(tmp_path, names: list[str]) -> str:
    for name in names:
        (tmp_path / name / ".git").mkdir(parents=True)

    return f"{tmp_path.as_uri()}/*"


# ----------------------------------------------------------------------
class TestRepositories:
    # ----------------------------------------------------------------------
    # A single repository is audited under the same heading as each of several repositories.
    def test_HeadingForSingleRepository(self):
        result, output = _InvokeAndCapture(_SKIP_NETWORK)

        assert result.exit_code == 0, output
        assert "Auditing (1 of 1)..." in output

    # ----------------------------------------------------------------------
    # The experience audits every repository, so it is invoked once with all of them.
    def test_Wildcard(self, tmp_path):
        url = _CreateRepositories(tmp_path, ["Second", "First"])

        with mock.patch("RepoAuditorWeb.__main__.ExecuteConsoleExperience") as experience_mock:
            result, output = _InvokeAndCapture([*_SKIP_NETWORK, "--url", url, "--branch", "main"])

        assert result.exit_code == 0, output
        assert experience_mock.call_count == 1

        kwargs = experience_mock.call_args.kwargs

        assert kwargs["urls"] == [(tmp_path / name).resolve().as_uri() for name in ["First", "Second"]]
        assert kwargs["common_arguments"] == {"pat": None, "branch": "main"}

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("option", ["--include-archived", "--include-forked"])
    def test_ErrorIncludeOptionWithoutWildcard(self, option):
        result, output = _InvokeAndCapture(
            [*_SKIP_NETWORK, "--url", "https://github.com/gt-csse/RepoAuditorWeb", option],
        )

        assert result.exit_code != 0
        assert f"'{option}' is only valid with a GitHub url that ends with '/*'." in output


# ----------------------------------------------------------------------
class TestJsonDocument:
    # ----------------------------------------------------------------------
    def test_Repositories(self, tmp_path):
        url = _CreateRepositories(tmp_path, ["First", "Second"])

        result = CliRunner().invoke(app, ["--experience", "json", "--url", url, "--pat", "my_pat"])

        assert result.exit_code == 0, result.output

        document = json.loads(result.stdout)

        assert document["error"] is None
        assert [repository["common_arguments"] for repository in document["repositories"]] == [
            {"url": (tmp_path / name).resolve().as_uri(), "pat": "***", "branch": None}
            for name in ["First", "Second"]
        ]

    # ----------------------------------------------------------------------
    # The experience writes the document, so a failure before it is invoked produces none.
    def test_NoDocumentForErrorBeforeExperience(self):
        result = CliRunner().invoke(
            app,
            [
                "--experience",
                "json",
                "--url",
                "https://github.com/gt-csse/RepoAuditorWeb",
                "--include-forked",
            ],
        )

        assert result.exit_code != 0
        assert result.stdout == ""
        assert "'--include-forked' is only valid with a GitHub url that ends with '/*'." in result.stderr
