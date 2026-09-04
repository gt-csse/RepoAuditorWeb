import asyncio
import json
import re
import threading

from typing import cast, override

import pytest

from fastapi import HTTPException
from fastapi.routing import APIRoute
from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResultValue
from RepoAuditorWeb.web_experience_impl.server import CreateApp

from conftest import EvaluateValues, MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
_CONFIG_REGEX = re.compile(
    r'<script id="config" type="application/json">(?P<config>.*?)</script>',
    re.DOTALL,
)

_TOKEN = "my_token"


# ----------------------------------------------------------------------
# starlette's TestClient requires a dependency that the package does not take, so the route's
# handler is invoked through the app's route table instead.
def _GetEndpoint(app, path: str):
    return next(route.endpoint for route in app.routes if route.path == path)


# ----------------------------------------------------------------------
def _GetIndex(app) -> dict[str, object]:
    match = _CONFIG_REGEX.search(_GetEndpoint(app, "/")())
    assert match is not None

    return json.loads(match.group("config"))


# ----------------------------------------------------------------------
def _CreateApp(*, execute: bool) -> object:
    return CreateApp([], DynamicParameters([]), {}, _TOKEN, execute=execute)


# ----------------------------------------------------------------------
def _CreateModule(
    name: str = "MyModule",
    evaluate_values: EvaluateValues | None = None,
) -> MyModule:
    requirement = MyRequirement(
        "MyRequirement",
        "My requirement description.",
        evaluate_values=evaluate_values,
    )

    return MyModule(
        name,
        "My description.",
        [MyQuery("MyQuery", [requirement], query_data={})],
        parameters={"one": TyperParameter(str, "default", OptionInfo(help="One"))},
    )


# ----------------------------------------------------------------------
# StreamingResponse adapts the generator it is given to the async iteration that serving a request
# performs, so consuming it requires an event loop.
def _Consume(response) -> list[dict[str, object]]:
    # ----------------------------------------------------------------------
    async def Collect() -> list[str]:
        return [chunk async for chunk in response.body_iterator]

    # ----------------------------------------------------------------------

    return [json.loads(chunk.removeprefix("data: ").rstrip("\n")) for chunk in asyncio.run(Collect())]


# ----------------------------------------------------------------------
# The execution runs on a thread of its own, so the events it produces are collected by consuming
# the stream until the run closes the sink.
def _Execute(app, arguments: dict[str, object]) -> list[dict[str, object]]:
    assert _GetEndpoint(app, "/api/execute")(arguments, _TOKEN) == {"status": "started"}

    return _Consume(_GetEndpoint(app, "/api/stream")(_TOKEN))


# ----------------------------------------------------------------------
# The events arrive as decoded JSON, so the values they carry are asserted to be the strings the
# tests compare against.
def _GetContent(events: list[dict[str, object]], event_type: str, key: str) -> list[str]:
    values = [event[key] for event in events if event["type"] == event_type]

    assert all(isinstance(value, str) for value in values), values

    return cast("list[str]", values)


# ----------------------------------------------------------------------
def test_NoExecuteByDefault():
    assert _GetIndex(CreateApp([], DynamicParameters([]), {}, _TOKEN))["execute"] is False


# ----------------------------------------------------------------------
def test_Execute():
    assert _GetIndex(_CreateApp(execute=True))["execute"] is True


# ----------------------------------------------------------------------
# A reload must not run again on the user's behalf.
def test_ExecuteAppliesToInitialDisplayOnly():
    app = _CreateApp(execute=True)

    assert _GetIndex(app)["execute"] is True
    assert _GetIndex(app)["execute"] is False


# ----------------------------------------------------------------------
def test_TokenIsSuppliedToThePage():
    assert _GetIndex(_CreateApp(execute=False))["token"] == _TOKEN


# ----------------------------------------------------------------------
# The handler is invoked directly by the tests below, which bypasses the validation FastAPI
# performs against the body, so the name the page submits under is asserted against the name the
# route declares.
def test_ExecuteBodyMatchesWhatThePageSubmits():
    app = CreateApp([], DynamicParameters([]), {}, _TOKEN)

    route = next(
        route for route in app.routes if isinstance(route, APIRoute) and route.path == "/api/execute"
    )
    names = [field.alias for field in route.dependant.body_params]

    assert names == ["arguments"]
    assert "JSON.stringify({ arguments: CollectArguments() })" in _GetEndpoint(app, "/")()


# ----------------------------------------------------------------------
class TestFields:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        app = CreateApp([], DynamicParameters([]), {}, _TOKEN)

        assert _GetEndpoint(app, "/api/fields")(_TOKEN) == {"groups": []}

    # ----------------------------------------------------------------------
    def test_Groups(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        groups = _GetEndpoint(app, "/api/fields")(_TOKEN)["groups"]

        assert len(groups) == 1
        assert groups[0]["name"] == "MyModule"
        assert [field["name"] for field in groups[0]["fields"]] == ["MyModule_skip", "MyModule_one"]

        assert [section["name"] for section in groups[0]["sections"]] == ["MyRequirement"]
        assert [field["name"] for field in groups[0]["sections"][0]["fields"]] == [
            "MyModule_MyRequirement_skip",
        ]

    # ----------------------------------------------------------------------
    def test_Descriptions(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        groups = _GetEndpoint(app, "/api/fields")(_TOKEN)["groups"]

        assert groups[0]["description"] == "My description."
        assert groups[0]["sections"][0]["description"] == "My requirement description."

    # ----------------------------------------------------------------------
    def test_ValuesAreDisplayed(self):
        module = _CreateModule()
        app = CreateApp(
            [module],
            DynamicParameters([module]),
            {"MyModule": {None: {"one": "provided"}}},
            _TOKEN,
        )

        fields = _GetEndpoint(app, "/api/fields")(_TOKEN)["groups"][0]["fields"]

        assert next(field for field in fields if field["name"] == "MyModule_one")["value"] == "provided"


# ----------------------------------------------------------------------
# The server is reachable by any process on the machine, so the endpoints that execute work are
# gated by a token that only this process and the window it opened know about.
class TestToken:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("token", ["other_token", None])
    @pytest.mark.parametrize("path", ["/api/fields", "/api/stream"])
    def test_ErrorInvalidToken(self, path, token):
        app = _CreateApp(execute=False)

        with pytest.raises(HTTPException) as exc_info:
            _GetEndpoint(app, path)(token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token."

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("token", ["other_token", None])
    def test_ErrorInvalidTokenOnExecute(self, token):
        app = _CreateApp(execute=False)

        with pytest.raises(HTTPException) as exc_info:
            _GetEndpoint(app, "/api/execute")({}, token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid token."

    # ----------------------------------------------------------------------
    # The page itself carries no token because it is what receives one.
    def test_IndexRequiresNoToken(self):
        assert _GetIndex(_CreateApp(execute=False)) is not None


# ----------------------------------------------------------------------
class TestStream:
    # ----------------------------------------------------------------------
    def test_ErrorWhenNothingIsRunning(self):
        app = _CreateApp(execute=False)

        with pytest.raises(HTTPException) as exc_info:
            _GetEndpoint(app, "/api/stream")(_TOKEN)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "No execution is in progress."

    # ----------------------------------------------------------------------
    # Buffering an event stream defeats its purpose, so the intermediaries that would do so are
    # instructed not to.
    def test_Headers(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        assert _GetEndpoint(app, "/api/execute")({}, _TOKEN) == {"status": "started"}

        response = _GetEndpoint(app, "/api/stream")(_TOKEN)

        assert response.media_type == "text/event-stream"
        assert response.headers["cache-control"] == "no-cache"
        assert response.headers["x-accel-buffering"] == "no"

        # Consume the stream so that the run releases the lock before the test ends.
        _Consume(response)

    # ----------------------------------------------------------------------
    # The enumeration is terminated by an event of its own so that the page knows the run finished
    # rather than inferring it from the connection closing.
    def test_DoneIsTheFinalEvent(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        assert _Execute(app, {})[-1] == {"type": "done"}


# ----------------------------------------------------------------------
class TestExecution:
    # ----------------------------------------------------------------------
    def test_OutputIsStreamed(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        output = "".join(_GetContent(_Execute(app, {}), "output", "content"))

        assert "Executing module 'MyModule' (1 of 1)..." in output

    # ----------------------------------------------------------------------
    def test_ResultsAreRendered(self):
        module = _CreateModule(evaluate_values=EvaluateValues(EvaluateResultValue.Error))
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        results = _GetContent(_Execute(app, {}), "results", "html")

        assert len(results) == 1
        assert '<span class="module">MyModule</span>' in results[0]

    # ----------------------------------------------------------------------
    def test_ResolutionAndRationaleAreOmittedWhenNotDisplayed(self):
        module = _CreateModule(
            evaluate_values=EvaluateValues(
                EvaluateResultValue.Error,
                resolution="Do this.",
                rationale="Because of that.",
            ),
        )

        app = CreateApp(
            [module],
            DynamicParameters([module]),
            {},
            _TOKEN,
            display_resolution=False,
            display_rationale=False,
        )

        html = _GetContent(_Execute(app, {}), "results", "html")[0]

        assert 'class="resolution"' not in html
        assert 'class="rationale"' not in html

    # ----------------------------------------------------------------------
    # Successful requirements are rendered only when everything was requested.
    def test_Verbose(self):
        module = _CreateModule()

        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN, verbose=True)

        html = _GetContent(_Execute(app, {}), "results", "html")[0]

        assert '<span class="module">MyModule</span>' in html

    # ----------------------------------------------------------------------
    def test_Debug(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN, debug=True)

        assert _Execute(app, {})[-1] == {"type": "done"}

    # ----------------------------------------------------------------------
    # The run happens on a thread of its own, so a failure is reported to the page rather than
    # terminating the thread silently.
    def test_ErrorIsStreamed(self):
        requirement = MyRequirement("MyRequirement", "My requirement description.")
        module = MyModule(
            "MyModule",
            "My description.",
            [MyQuery("MyQuery", [requirement], query_data={})],
            parameters={"one": TyperParameter(int, 0, OptionInfo(help="One"))},
        )

        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        errors = _GetContent(_Execute(app, {"MyModule_one": "not_a_number"}), "error", "message")

        assert len(errors) == 1
        assert "not_a_number" in errors[0]

    # ----------------------------------------------------------------------
    # A failure still terminates the stream so that the page stops waiting for output.
    def test_StreamIsClosedAfterAnError(self):
        requirement = MyRequirement("MyRequirement", "My requirement description.")
        module = MyModule(
            "MyModule",
            "My description.",
            [MyQuery("MyQuery", [requirement], query_data={})],
            parameters={"one": TyperParameter(int, 0, OptionInfo(help="One"))},
        )

        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        assert _Execute(app, {"MyModule_one": "not_a_number"})[-1] == {"type": "done"}

    # ----------------------------------------------------------------------
    # A reload restores what the user entered rather than reverting to the values the experience
    # started with.
    def test_SubmittedValuesAreRetained(self):
        module = _CreateModule()
        values: dict[str, dict[str | None, dict[str, object]]] = {}
        app = CreateApp([module], DynamicParameters([module]), values, _TOKEN)

        _Execute(app, {"MyModule_one": "provided"})

        fields = _GetEndpoint(app, "/api/fields")(_TOKEN)["groups"][0]["fields"]

        assert next(field for field in fields if field["name"] == "MyModule_one")["value"] == "provided"

    # ----------------------------------------------------------------------
    # A second request must not interleave its output into the stream of the first.
    def test_ErrorWhenAlreadyRunning(self):
        # The lock is held only while a run is underway, so the module blocks the first run until
        # the second request has been rejected.
        release = threading.Event()
        started = threading.Event()

        # ----------------------------------------------------------------------
        class BlockingQuery(MyQuery):
            @override
            def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object]:
                started.set()
                assert release.wait(timeout=5)

                return {}

        # ----------------------------------------------------------------------

        requirement = MyRequirement("MyRequirement", "My requirement description.")
        module = MyModule(
            "MyModule",
            "My description.",
            [BlockingQuery("MyQuery", [requirement])],
        )

        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)
        endpoint = _GetEndpoint(app, "/api/execute")

        assert endpoint({}, _TOKEN) == {"status": "started"}
        assert started.wait(timeout=5)

        try:
            with pytest.raises(HTTPException) as exc_info:
                endpoint({}, _TOKEN)

            assert exc_info.value.status_code == 409
            assert exc_info.value.detail == "An execution is already in progress."
        finally:
            release.set()

        # Consume the stream so that the run releases the lock before the test ends.
        _Consume(_GetEndpoint(app, "/api/stream")(_TOKEN))

    # ----------------------------------------------------------------------
    # The lock is released once a run completes, so the next one is admitted.
    def test_RunsAreSequential(self):
        module = _CreateModule()
        app = CreateApp([module], DynamicParameters([module]), {}, _TOKEN)

        assert _Execute(app, {})[-1] == {"type": "done"}
        assert _Execute(app, {})[-1] == {"type": "done"}
