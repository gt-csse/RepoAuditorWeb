from typing import TYPE_CHECKING

from RepoAuditorWeb.tui_experience_impl.app import AuditorApp

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
def ExecuteExperience(
    dm: DoneManager,
    port: int,  # noqa: ARG001
    token: str,  # noqa: ARG001
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    *,
    execute: bool = False,
    evaluate_all: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> None:
    """Execute the application in a TUI experience."""

    # The application takes over the terminal, so nothing is written to the DoneManager's stream
    # while it runs; the flags it was created with govern what the application displays.
    app = AuditorApp(
        modules,
        dynamic_parameters,
        arguments,
        execute=execute,
        evaluate_all=evaluate_all,
        display_resolution=display_resolution,
        display_rationale=display_rationale,
        verbose=dm.is_verbose,
        debug=dm.is_debug,
    )

    with dm.Nested("Running the terminal application..."):
        app.run()
