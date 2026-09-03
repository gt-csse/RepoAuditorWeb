from enum import StrEnum
from typing import Annotated

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from typer.core import TyperGroup

from RepoAuditorWeb.console_experience import ExecuteExperience as ExecuteConsoleExperience
from RepoAuditorWeb.impl import entry_point_utils
from RepoAuditorWeb.web_experience import ExecuteExperience as ExecuteWebExperience
from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
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
    Web = "web"


# ----------------------------------------------------------------------
_dynamic_parameters = DynamicParameters(MODULES)


# ----------------------------------------------------------------------
@entry_point_utils.dynamic_command(app, _dynamic_parameters.dynamic_parameters, no_args_is_help=False)
def EntryPoint(
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

    with DoneManager.CreateCommandLine(
        flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
    ) as dm:
        port = entry_point_utils.ResolvePort(port)
        token = entry_point_utils.ResolveToken(token)
        arguments = _dynamic_parameters.Parse(kwargs)

        experience_kwargs = {
            "dm": dm,
            "port": port,
            "token": token,
            "modules": MODULES,
            "dynamic_parameters": _dynamic_parameters,
            "arguments": arguments,
            "execute": execute,
            "display_resolution": not no_resolution,
            "display_rationale": not no_rationale,
        }

        if experience == Experience.Console:
            ExecuteConsoleExperience(**experience_kwargs)
        elif experience == Experience.Web:
            ExecuteWebExperience(**experience_kwargs)
        else:
            assert False, experience  # noqa: B011, PT015  # pragma: no cover


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover
