"""Contains the FastAPI application that backs the web experience."""

import dataclasses
import json
import threading

from typing import Annotated, TYPE_CHECKING

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from RepoAuditorWeb.lib.execute import Execute
from RepoAuditorWeb.web_experience_impl import form, results_html
from RepoAuditorWeb.web_experience_impl.page import CreatePage
from RepoAuditorWeb.web_experience_impl.stream_sink import StreamSink

if TYPE_CHECKING:
    from collections.abc import Iterator

    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
def CreateApp(
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    token: str,
    *,
    execute: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
    verbose: bool = False,
    debug: bool = False,
) -> FastAPI:
    """Create the application that serves the web experience."""

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    # Only one run may be in flight at a time; the page disables its control while a run is active,
    # but the server enforces it so that a second request cannot interleave output into the stream.
    lock = threading.Lock()
    state: dict[str, object] = {"sink": None, "execute": execute}

    # ----------------------------------------------------------------------
    def VerifyToken(token_header: str | None) -> None:
        # The server is reachable by any process on the machine, so a token that only this process
        # and the window it opened know about gates the endpoints that execute work.
        if token_header != token:
            raise HTTPException(status_code=401, detail="Invalid token.")

    # ----------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def Index() -> str:
        # Automatic execution applies to the initial display only; a reload once the experience is
        # underway restores what the user entered without running again on their behalf.
        execute_on_load = bool(state["execute"])
        state["execute"] = False

        return CreatePage(
            form.CreateGroups(dynamic_parameters, arguments),
            token,
            execute=execute_on_load,
        )

    # ----------------------------------------------------------------------
    @app.get("/api/fields")
    def GetFields(x_auditor_token: Annotated[str | None, Header()] = None) -> dict[str, object]:
        VerifyToken(x_auditor_token)

        return {
            "groups": [
                dataclasses.asdict(group) for group in form.CreateGroups(dynamic_parameters, arguments)
            ],
        }

    # ----------------------------------------------------------------------
    @app.post("/api/execute")
    def PostExecute(
        # The page submits the values under 'arguments'; the parameter is named for what it holds,
        # so the name the body uses is pinned rather than derived from it.
        submitted: Annotated[dict[str, object], Body(embed=True, alias="arguments")],
        x_auditor_token: Annotated[str | None, Header()] = None,
    ) -> dict[str, object]:
        VerifyToken(x_auditor_token)

        if not lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="An execution is already in progress.")

        sink = StreamSink()
        state["sink"] = sink

        thread = threading.Thread(
            target=_Run,
            args=(sink, lock, modules, dynamic_parameters, arguments, submitted),
            kwargs={
                "display_resolution": display_resolution,
                "display_rationale": display_rationale,
                "verbose": verbose,
                "debug": debug,
            },
            daemon=True,
        )
        thread.start()

        return {"status": "started"}

    # ----------------------------------------------------------------------
    @app.get("/api/stream")
    def GetStream(token: str) -> StreamingResponse:
        # EventSource cannot set headers, so the token is supplied as a query parameter.
        VerifyToken(token)

        sink = state.get("sink")
        if sink is None:
            raise HTTPException(status_code=409, detail="No execution is in progress.")

        assert isinstance(sink, StreamSink), sink

        return StreamingResponse(
            _EnumerateEvents(sink),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ----------------------------------------------------------------------

    return app


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _Run(
    sink: StreamSink,
    lock: threading.Lock,
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    submitted: dict[str, object],
    *,
    display_resolution: bool,
    display_rationale: bool,
    verbose: bool,
    debug: bool,
) -> None:
    try:
        # A value that cannot be coerced is reported through the stream rather than as a failed
        # request, so the conversion happens here. The result is retained so that a reload of the
        # page restores what the user entered rather than the values the experience started with.
        arguments.clear()
        arguments.update(form.ParseValues(dynamic_parameters, submitted))

        with DoneManager.Create(
            sink,
            "Executing...",
            flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
        ) as dm:
            results = Execute(dm, modules, arguments)

        sink.Send(
            "results",
            {
                "html": results_html.RenderResults(
                    results,
                    display_resolution=display_resolution,
                    display_rationale=display_rationale,
                    verbose=verbose,
                ),
            },
        )
    except Exception as ex:
        sink.Send("error", {"message": str(ex)})
    finally:
        sink.Close()
        lock.release()


# ----------------------------------------------------------------------
def _EnumerateEvents(sink: StreamSink) -> Iterator[str]:
    for event_type, data in sink.Enumerate():
        yield _CreateEvent(event_type, data)

    yield _CreateEvent("done", {})


# ----------------------------------------------------------------------
def _CreateEvent(event_type: str, data: dict[str, object]) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"
