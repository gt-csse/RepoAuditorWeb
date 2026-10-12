"""Contains the FastAPI application that backs the web experience."""

import dataclasses
import json
import secrets
import threading

from pathlib import Path
from typing import Annotated, TYPE_CHECKING

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from fastapi import Body, FastAPI, Header, HTTPException, Query
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from RepoAuditorWeb.lib import form
from RepoAuditorWeb.lib.execute import Execute
from RepoAuditorWeb.web_experience_impl import results_html
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
    evaluate_all: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
    verbose: bool = False,
    debug: bool = False,
) -> FastAPI:
    """Create the application that serves the web experience."""

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    # A page on another site could otherwise reach the server through a hostname that it rebinds
    # to the loopback address, which the browser would treat as same-origin with that page.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[HOST])

    # Only one run may be in flight at a time; the page disables its control while a run is active,
    # but the server enforces it so that a second request cannot interleave output into the stream.
    lock = threading.Lock()
    state: dict[str, object] = {"sink": None, "execute": execute}

    # A run replaces the retained values while pages are served on other threads; without this, a
    # page could render the defaults or a mix of the previous and submitted values.
    arguments_lock = threading.Lock()

    # ----------------------------------------------------------------------
    def CreateGroups() -> list[form.FormGroup]:
        with arguments_lock:
            return form.CreateGroups(dynamic_parameters, arguments)

    # ----------------------------------------------------------------------
    def VerifyToken(token_header: str | None) -> None:
        # The server is reachable by any process on the machine, so a token that only this process
        # and the window it opened know about gates the endpoints that execute work.
        if token_header is None or not secrets.compare_digest(token_header, token):
            raise HTTPException(status_code=401, detail="Invalid token.")

    # ----------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def Index(token_query: Annotated[str | None, Query(alias="token")] = None) -> str:
        # The page embeds the token and the values entered (including the PAT), so it is gated as
        # well; the window is opened with the token in its URL.
        VerifyToken(token_query)

        # Automatic execution applies to the initial display only; a reload once the experience is
        # underway restores what the user entered without running again on their behalf. Removing
        # the flag in a single operation ensures that concurrent loads cannot both observe it.
        execute_on_load = bool(state.pop("execute", False))

        return CreatePage(
            CreateGroups(),
            token,
            execute=execute_on_load,
        )

    # ----------------------------------------------------------------------
    @app.get("/icon.svg")
    def GetIcon() -> FileResponse:
        return FileResponse(_ICON_PATH, media_type="image/svg+xml")

    # ----------------------------------------------------------------------
    @app.get("/api/fields")
    def GetFields(x_auditor_token: Annotated[str | None, Header()] = None) -> dict[str, object]:
        VerifyToken(x_auditor_token)

        return {
            "groups": [dataclasses.asdict(group) for group in CreateGroups()],
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

        # _Run releases the lock once started; until then, a failure here would hold it indefinitely.
        try:
            sink = StreamSink()
            state["sink"] = sink

            thread = threading.Thread(
                target=_Run,
                args=(sink, lock, arguments_lock, modules, dynamic_parameters, arguments, submitted),
                kwargs={
                    "evaluate_all": evaluate_all,
                    "display_resolution": display_resolution,
                    "display_rationale": display_rationale,
                    "verbose": verbose,
                    "debug": debug,
                },
                daemon=True,
            )
            thread.start()
        except BaseException:
            lock.release()
            raise

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
HOST = "127.0.0.1"

_ICON_PATH = Path(__file__).parent / "icon.svg"


# ----------------------------------------------------------------------
def _Run(  # noqa: PLR0913
    sink: StreamSink,
    lock: threading.Lock,
    arguments_lock: threading.Lock,
    modules: list[Module],
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    submitted: dict[str, object],
    *,
    evaluate_all: bool,
    display_resolution: bool,
    display_rationale: bool,
    verbose: bool,
    debug: bool,
) -> None:
    try:
        # A value that cannot be coerced is reported through the stream rather than as a failed
        # request, so the conversion happens here. The result is retained so that a reload of the
        # page restores what the user entered rather than the values the experience started with.
        # The values are parsed before the retained ones are replaced so that a failure leaves them
        # intact.
        parsed = form.ParseValues(dynamic_parameters, submitted)

        with arguments_lock:
            arguments.clear()
            arguments.update(parsed)

        with DoneManager.Create(
            sink,
            "Executing...",
            flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
        ) as dm:
            results = Execute(dm, modules, arguments, evaluate_all=evaluate_all)

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
        # Closing the sink tells subscribers the run is done, which invites the next one, so the
        # lock must already be free when that happens.
        lock.release()
        sink.Close()


# ----------------------------------------------------------------------
def _EnumerateEvents(sink: StreamSink) -> Iterator[str]:
    for event_type, data in sink.Enumerate():
        yield _CreateEvent(event_type, data)

    yield _CreateEvent("done", {})


# ----------------------------------------------------------------------
def _CreateEvent(event_type: str, data: dict[str, object]) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"
