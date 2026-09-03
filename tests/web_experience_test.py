import io

from collections.abc import Mapping
from unittest import mock

import pytest

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.web_experience import ExecuteExperience

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateModule() -> MyModule:
    return MyModule(
        "MyModule",
        "My description.",
        [MyQuery("MyQuery", [MyRequirement("MyRequirement", "My requirement description.")])],
        parameters={"one": TyperParameter(str, "default")},
    )


# ----------------------------------------------------------------------
# The window and the server both run for as long as the user keeps the window open, so both are
# replaced by doubles that return immediately.
def _Invoke(
    modules: list[Module],
    arguments: dict[str, dict[str | None, dict[str, object]]],
    *,
    verbose: bool = False,
    debug: bool = False,
    **kwargs,
) -> tuple[mock.MagicMock, mock.MagicMock, str]:
    sink = io.StringIO()

    with (
        mock.patch("RepoAuditorWeb.web_experience.webview") as webview_mock,
        mock.patch("RepoAuditorWeb.web_experience.uvicorn") as uvicorn_mock,
        DoneManager.Create(
            sink,
            "Testing...",
            flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
        ) as dm,
    ):
        ExecuteExperience(dm, 8080, "my_token", modules, DynamicParameters(modules), arguments, **kwargs)

    return webview_mock, uvicorn_mock, sink.getvalue()


# ----------------------------------------------------------------------
def test_WindowIsOpened():
    webview_mock, _, _ = _Invoke([], {})

    assert webview_mock.create_window.call_args.args == ("RepoAuditor", "http://127.0.0.1:8080/")
    assert webview_mock.start.call_count == 1


# ----------------------------------------------------------------------
# The window's web inspector is available when the caller ran with debug output.
@pytest.mark.parametrize("debug", [True, False])
def test_WindowDebugMatchesTheDoneManager(debug):
    webview_mock, _, _ = _Invoke([], {}, debug=debug)

    assert webview_mock.start.call_args.kwargs["debug"] is debug


# ----------------------------------------------------------------------
def test_ServerIsConfigured():
    _, uvicorn_mock, _ = _Invoke([], {})

    kwargs = uvicorn_mock.Config.call_args.kwargs

    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 8080


# ----------------------------------------------------------------------
# The application runs until the window is closed, at which point the server is no longer needed.
def test_ServerIsStoppedWhenTheWindowCloses():
    _, uvicorn_mock, _ = _Invoke([], {})

    assert uvicorn_mock.Server.return_value.should_exit is True


# ----------------------------------------------------------------------
def test_UrlIsWritten():
    _, _, output = _Invoke([], {})

    assert "Serving content on http://127.0.0.1:8080..." in output


# ----------------------------------------------------------------------
def test_WindowClosingIsWrittenWhenVerbose():
    _, _, output = _Invoke([], {}, verbose=True)

    assert "The window was closed." in output


# ----------------------------------------------------------------------
class TestApp:
    # ----------------------------------------------------------------------
    @staticmethod
    def _InvokeAndCaptureKwargs(**kwargs) -> tuple[tuple, Mapping[str, object]]:
        module = _CreateModule()

        with mock.patch("RepoAuditorWeb.web_experience.CreateApp") as create_app_mock:
            _Invoke([module], {"MyModule": {None: {"one": "provided"}}}, **kwargs)

        assert create_app_mock.call_count == 1

        return create_app_mock.call_args.args, create_app_mock.call_args.kwargs

    # ----------------------------------------------------------------------
    def test_ModulesAndTokenAreForwarded(self):
        args, _ = self._InvokeAndCaptureKwargs()

        assert args[0][0].name == "MyModule"
        assert args[3] == "my_token"

    # ----------------------------------------------------------------------
    # The values a run starts with are displayed for editing.
    def test_ArgumentsAreForwarded(self):
        args, _ = self._InvokeAndCaptureKwargs()

        assert args[2] == {"MyModule": {None: {"one": "provided"}}}

    # ----------------------------------------------------------------------
    def test_Defaults(self):
        _, kwargs = self._InvokeAndCaptureKwargs()

        assert kwargs["execute"] is False
        assert kwargs["display_resolution"] is True
        assert kwargs["display_rationale"] is True
        assert kwargs["verbose"] is False
        assert kwargs["debug"] is False

    # ----------------------------------------------------------------------
    def test_Execute(self):
        assert self._InvokeAndCaptureKwargs(execute=True)[1]["execute"] is True

    # ----------------------------------------------------------------------
    def test_NoResolution(self):
        kwargs = self._InvokeAndCaptureKwargs(display_resolution=False)[1]

        assert kwargs["display_resolution"] is False

    # ----------------------------------------------------------------------
    def test_NoRationale(self):
        kwargs = self._InvokeAndCaptureKwargs(display_rationale=False)[1]

        assert kwargs["display_rationale"] is False

    # ----------------------------------------------------------------------
    # The flags the caller ran with govern what the page displays.
    def test_VerboseAndDebugAreTakenFromTheDoneManager(self):
        kwargs = self._InvokeAndCaptureKwargs(verbose=True, debug=True)[1]

        assert kwargs["verbose"] is True
        assert kwargs["debug"] is True
