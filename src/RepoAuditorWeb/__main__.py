from typing import Annotated

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from typer.core import TyperGroup

from RepoAuditorWeb.impl import entry_point_utils
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

    port = entry_point_utils.ResolvePort(port)
    token = entry_point_utils.ResolveToken(token)
    parameter_values = _dynamic_parameters.Parse(kwargs)

    with DoneManager.CreateCommandLine(
        flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
    ) as dm:
        dm.WriteInfo(str(parameter_values))


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover
