import threading

from typing import TYPE_CHECKING

import uvicorn
import webview

from RepoAuditorWeb.web_experience_impl.server import CreateApp

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
def ExecuteExperience(
    dm: DoneManager,
    port: int,
    token: str,
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    *,
    execute: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> None:
    """Execute the application in a web experience."""

    app = CreateApp(
        modules,
        dynamic_parameters,
        arguments,
        token,
        execute=execute,
        display_resolution=display_resolution,
        display_rationale=display_rationale,
        verbose=dm.is_verbose,
        debug=dm.is_debug,
    )

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"),
    )

    # The window must run on the main thread, so the server is what moves to a background thread.
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    with dm.Nested(f"Serving content on http://127.0.0.1:{port}...") as serve_dm:
        webview.create_window("RepoAuditor", f"http://127.0.0.1:{port}/")

        # Debug mode enables the web inspector within the window.
        webview.start(debug=dm.is_debug)

        serve_dm.WriteVerbose("The window was closed.\n")

    # The application runs until the window is closed, at which point the server is no longer needed.
    server.should_exit = True
    server_thread.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_SHUTDOWN_TIMEOUT_SECONDS = 5.0
