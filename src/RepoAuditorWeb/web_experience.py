import threading
import time

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import uvicorn
import webview

from RepoAuditorWeb.impl.entry_point_utils import ResolvePort
from RepoAuditorWeb.impl.repositories import InvokeForEachRepository
from RepoAuditorWeb.web_experience_impl.server import CreateApp, HOST

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
def ExecuteExperience(  # noqa: PLR0913
    dm: DoneManager,
    port: int | None,
    token: str,
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    common_arguments: dict[str, object],
    urls: list[str | None],
    *,
    execute: bool = False,
    evaluate_all: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> None:
    """Execute the application in a web experience, opening a window for each repository."""

    if len(urls) > 1 and not execute:
        dm.WriteWarning(
            f"A window is opened for each of the {len(urls)} repositories in turn; use '--execute' to run each audit without waiting for it to be invoked.\n\n",
        )

    InvokeForEachRepository(
        dm,
        modules,
        arguments,
        common_arguments,
        urls,
        lambda repository_dm, repository_arguments, repository_common_arguments: _ExecuteRepository(
            repository_dm,
            # A server from a previous repository may still hold its port while shutting down, so a
            # new port is chosen unless one was provided.
            ResolvePort(port),
            token,
            modules,
            dynamic_parameters,
            repository_arguments,
            repository_common_arguments,
            execute=execute,
            evaluate_all=evaluate_all,
            display_resolution=display_resolution,
            display_rationale=display_rationale,
        ),
    )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_SHUTDOWN_TIMEOUT_SECONDS = 5.0
_STARTUP_POLL_SECONDS = 0.05
_ICON_PATH = Path(__file__).parent / "web_experience_impl" / "icon.ico"


# ----------------------------------------------------------------------
def _ExecuteRepository(  # noqa: PLR0913
    dm: DoneManager,
    port: int,
    token: str,
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    common_arguments: dict[str, object],
    *,
    execute: bool,
    evaluate_all: bool,
    display_resolution: bool,
    display_rationale: bool,
) -> None:
    app = CreateApp(
        modules,
        dynamic_parameters,
        arguments,
        common_arguments,
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

    # The server is stopped even when the window fails, as the process may continue (for example, to
    # audit the next repository) and the server would otherwise keep its port.
    try:
        with dm.Nested(f"Serving content on http://{HOST}:{port}...") as serve_dm:
            webview.create_window("RepoAuditor", f"http://{HOST}:{port}/?{urlencode({'token': token})}")

            # Debug mode enables the web inspector within the window. The icon is an ICO file because
            # that is the only format the Windows backend loads.
            webview.start(debug=dm.is_debug, icon=str(_ICON_PATH))

            serve_dm.WriteVerbose("The window was closed.\n")
    finally:
        # The application runs until the window is closed, at which point the server is no longer needed.
        server.should_exit = True
        server_thread.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
