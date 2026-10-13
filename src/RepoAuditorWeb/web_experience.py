import threading
import time

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import uvicorn
import webview

from RepoAuditorWeb.web_experience_impl.server import CreateApp, HOST

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
    evaluate_all: bool = False,
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
        evaluate_all=evaluate_all,
        display_resolution=display_resolution,
        display_rationale=display_rationale,
        verbose=dm.is_verbose,
        debug=dm.is_debug,
    )

    server = uvicorn.Server(
        uvicorn.Config(app, host=HOST, port=port, log_level="warning"),
    )

    # The window must run on the main thread, so the server is what moves to a background thread.
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    # The window would otherwise load the page before the server is listening and display an error.
    # uvicorn ends the thread when it cannot bind the port.
    while not server.started:
        if not server_thread.is_alive():
            msg = f"The server could not be started on port {port}."
            raise RuntimeError(msg)

        time.sleep(_STARTUP_POLL_SECONDS)

    with dm.Nested(f"Serving content on http://{HOST}:{port}...") as serve_dm:
        webview.create_window("RepoAuditor", f"http://{HOST}:{port}/?{urlencode({'token': token})}")

        # Debug mode enables the web inspector within the window. The icon is an ICO file because
        # that is the only format the Windows backend loads.
        webview.start(debug=dm.is_debug, icon=str(_ICON_PATH))

        serve_dm.WriteVerbose("The window was closed.\n")

    # The application runs until the window is closed, at which point the server is no longer needed.
    server.should_exit = True
    server_thread.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_SHUTDOWN_TIMEOUT_SECONDS = 5.0
_STARTUP_POLL_SECONDS = 0.05
_ICON_PATH = Path(__file__).parent / "web_experience_impl" / "icon.ico"
