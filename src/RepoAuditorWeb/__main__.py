import sys

from enum import StrEnum
from typing import Annotated

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from typer.core import TyperGroup
from typer.models import OptionInfo

from RepoAuditorWeb.console_experience import ExecuteExperience as ExecuteConsoleExperience
from RepoAuditorWeb.impl import entry_point_utils
from RepoAuditorWeb.impl.repositories import DisableModulesWithoutUrl, ResolveRepositories
from RepoAuditorWeb.json_experience import (
    CreateRepositoryEntry as CreateJsonRepositoryEntry,
    ExecuteExperience as ExecuteJsonExperience,
    WriteDocument as WriteJsonDocument,
)
from RepoAuditorWeb.web_experience import ExecuteExperience as ExecuteWebExperience
from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.lib.modules import MODULES


# ----------------------------------------------------------------------
class NaturalOrderGrouper(TyperGroup):  # noqa: D101
    # ----------------------------------------------------------------------
    def list_commands(self, *args, **kwargs) -> list[str]:  # noqa: ARG002, D102
        return list(self.commands.keys())  # pragma: no cover


# ----------------------------------------------------------------------
app = typer.Typer(
    cls=NaturalOrderGrouper,
    help=__doc__,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
)


# ----------------------------------------------------------------------
class Experience(StrEnum):
    """The user's experience interacting with the application."""

    Console = "console"
    Json = "json"
    Web = "web"


# ----------------------------------------------------------------------
_URL_HELP = "GitHub URL (e.g. https://github.com/gt-csse/RepoAuditorWeb)."
_PAT_HELP = "GitHub Personal Access Token (PAT) or path to a local file containing the PAT."
_BRANCH_HELP = "Branch to evaluate. The default branch will be used if not specified."

_dynamic_parameters = DynamicParameters(
    MODULES,
    {
        "url": TyperParameter(str | None, None, OptionInfo(help=_URL_HELP)),
        "pat": TyperParameter(str | None, None, OptionInfo(help=_PAT_HELP)),
        "branch": TyperParameter(str | None, None, OptionInfo(help=_BRANCH_HELP)),
    },
)


# ----------------------------------------------------------------------
@entry_point_utils.dynamic_command(app, _dynamic_parameters.dynamic_parameters, no_args_is_help=False)
def EntryPoint(  # noqa: PLR0913, PLR0917
    url: Annotated[
        str | None,
        typer.Option(
            "--url",
            # Wildcards are expanded here, so they are described for this option but not for the
            # common value displayed by the web form.
            help=f"{_URL_HELP} End the url with '/*' to audit every repository of a GitHub owner or local directory.",
            envvar="REPO_AUDITOR_WEB_GITHUB_URL",
        ),
    ] = None,
    pat: Annotated[
        str | None,
        typer.Option(
            "--pat",
            help=_PAT_HELP,
            envvar="REPO_AUDITOR_WEB_GITHUB_PAT",
        ),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option(
            "--branch",
            help=_BRANCH_HELP,
            envvar="REPO_AUDITOR_WEB_GITHUB_BRANCH",
        ),
    ] = None,
    include_archived: Annotated[  # noqa: FBT002
        bool,
        typer.Option(
            "--include-archived",
            help="Include archived repositories when a GitHub url ends with '/*'.",
        ),
    ] = False,
    include_forked: Annotated[  # noqa: FBT002
        bool,
        typer.Option(
            "--include-forked",
            help="Include forked repositories when a GitHub url ends with '/*'.",
        ),
    ] = False,
    port: Annotated[
        int | None,
        typer.Option("--port", min=1024, max=65535, help="The port to run the server on."),
    ] = None,
    token: Annotated[
        str | None,
        typer.Option("--token", help="The token required to access protected endpoints."),
    ] = None,
    experience: Annotated[
        Experience,
        typer.Option(
            "--experience",
            case_sensitive=False,
            help=Experience.__doc__,
        ),
    ] = Experience.Web,
    execute: Annotated[  # noqa: FBT002
        bool,
        typer.Option(
            "--execute",
            help="Execute the experience immediately rather than waiting for the user to invoke it.",
        ),
    ] = False,
    evaluate_all: Annotated[  # noqa: FBT002
        bool,
        typer.Option(
            "--evaluate-all",
            help="Evaluate every requirement, including those that are otherwise suppressed because a parent setting is not enabled. This surfaces all failures in a single run.",
        ),
    ] = False,
    no_resolution: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--no-resolution", help="Do not display the resolution for each requirement."),
    ] = False,
    no_rationale: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--no-rationale", help="Do not display the rationale for each requirement."),
    ] = False,
    verbose: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--verbose", help="Write verbose information to the terminal."),
    ] = False,
    debug: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--debug", help="Write debug information to the terminal."),
    ] = False,
    version: Annotated[  # noqa: ARG001
        bool | None,
        typer.Option(
            "--version",
            callback=entry_point_utils.VersionCallback,
            is_eager=True,
            help="Display the version number and exit.",
        ),
    ] = None,
    **kwargs,
) -> None:
    """Invoke RepoAuditor."""

    # The json experience writes a document to stdout, so everything that DoneManager produces is
    # written to stderr in order to keep that document parsable.
    stream = sys.stderr if experience == Experience.Json else sys.stdout

    # The json experience contributes an entry per repository, and the document is written once
    # however the run ends so that it is always valid.
    json_entries: list[dict[str, object]] = []
    json_error: str | None = None

    # DoneManager raises typer.Exit when it exits, so the separator is written from a 'finally'
    # clause in order to land after the final status message rather than before it.
    try:
        with DoneManager.CreateCommandLine(
            stream,
            flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
        ) as dm:
            try:
                token = entry_point_utils.ResolveToken(token)
                arguments = _dynamic_parameters.Parse(kwargs)

                repositories = ResolveRepositories(
                    dm,
                    url,
                    pat,
                    include_archived=include_archived,
                    include_forked=include_forked,
                )

                if experience == Experience.Web and len(repositories) > 1 and not execute:
                    dm.WriteWarning(
                        f"A window is opened for each of the {len(repositories)} repositories in turn; use '--execute' to run each audit without waiting for it to be invoked.\n\n",
                    )

                for index, repository in enumerate(repositories):
                    with dm.Nested(
                        f"Auditing {'' if repository is None else f"'{repository}' "}({index + 1} of {len(repositories)})...",
                        suffix="\n",
                        suppress_exceptions=True,
                    ) as repository_dm:
                        repository_arguments = (
                            arguments if index == 0 else DisableModulesWithoutUrl(MODULES, arguments)
                        )
                        common_arguments: dict[str, object] = {
                            "url": repository,
                            "pat": pat,
                            "branch": branch,
                        }

                        try:
                            entry = _ExecuteExperience(
                                experience,
                                dm=repository_dm,
                                # A server from a previous repository may still hold its port while
                                # shutting down, so a new port is chosen unless one was provided.
                                port=entry_point_utils.ResolvePort(port),
                                token=token,
                                modules=MODULES,
                                dynamic_parameters=_dynamic_parameters,
                                arguments=repository_arguments,
                                common_arguments=common_arguments,
                                execute=execute,
                                evaluate_all=evaluate_all,
                                display_resolution=not no_resolution,
                                display_rationale=not no_rationale,
                            )

                            if entry is not None:
                                json_entries.append(entry)
                        except Exception as ex:
                            # DoneManager displays the failure and the remaining repositories are
                            # audited; the document records the failure in the repository's entry.
                            json_entries.append(
                                CreateJsonRepositoryEntry(
                                    repository_arguments,
                                    common_arguments,
                                    error=str(ex),
                                ),
                            )
                            raise
            except KeyboardInterrupt:
                json_error = "The run was interrupted."
                raise
            except Exception as ex:
                json_error = str(ex)
                raise
    finally:
        if experience == Experience.Json:
            # The status output and the document are written to different streams, so
            # whitespace is added to separate them when both are displayed together.
            stream.write("\n")

            WriteJsonDocument(json_entries, json_error)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _ExecuteExperience(
    experience: Experience,
    **experience_kwargs,
) -> dict[str, object] | None:
    if experience == Experience.Console:
        ExecuteConsoleExperience(**experience_kwargs)
    elif experience == Experience.Json:
        return ExecuteJsonExperience(**experience_kwargs)
    elif experience == Experience.Web:
        ExecuteWebExperience(**experience_kwargs)
    else:
        assert False, experience  # noqa: B011, PT015  # pragma: no cover

    return None


# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover
