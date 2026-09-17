import io

from collections.abc import Mapping
from unittest import mock

import pytest

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.tui_experience import ExecuteExperience

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
# The application runs for as long as the user keeps it open, so it is replaced by a double that
# returns immediately.
def _Invoke(
    modules: list[Module],
    arguments: dict[str, dict[str | None, dict[str, object]]],
    *,
    verbose: bool = False,
    debug: bool = False,
    **kwargs,
) -> tuple[mock.MagicMock, str]:
    sink = io.StringIO()

    with (
        mock.patch("RepoAuditorWeb.tui_experience.AuditorApp") as app_mock,
        DoneManager.Create(
            sink,
            "Testing...",
            flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
        ) as dm,
    ):
        ExecuteExperience(dm, 8080, "my_token", modules, DynamicParameters(modules), arguments, **kwargs)

    return app_mock, sink.getvalue()


# ----------------------------------------------------------------------
def test_ApplicationIsRun():
    app_mock, _ = _Invoke([], {})

    assert app_mock.return_value.run.call_count == 1


# ----------------------------------------------------------------------
def test_StatusIsWritten():
    _, output = _Invoke([], {})

    assert "Running the terminal application..." in output


# ----------------------------------------------------------------------
class TestApp:
    # ----------------------------------------------------------------------
    @staticmethod
    def _InvokeAndCaptureKwargs(**kwargs) -> tuple[tuple, Mapping[str, object]]:
        module = _CreateModule()

        app_mock, _ = _Invoke([module], {"MyModule": {None: {"one": "provided"}}}, **kwargs)

        assert app_mock.call_count == 1

        return app_mock.call_args.args, app_mock.call_args.kwargs

    # ----------------------------------------------------------------------
    def test_ModulesAreForwarded(self):
        args, _ = self._InvokeAndCaptureKwargs()

        assert args[0][0].name == "MyModule"

    # ----------------------------------------------------------------------
    # The values a run starts with are displayed for editing.
    def test_ArgumentsAreForwarded(self):
        args, _ = self._InvokeAndCaptureKwargs()

        assert args[2] == {"MyModule": {None: {"one": "provided"}}}

    # ----------------------------------------------------------------------
    def test_Defaults(self):
        _, kwargs = self._InvokeAndCaptureKwargs()

        assert kwargs["execute"] is False
        assert kwargs["evaluate_all"] is False
        assert kwargs["display_resolution"] is True
        assert kwargs["display_rationale"] is True
        assert kwargs["verbose"] is False
        assert kwargs["debug"] is False

    # ----------------------------------------------------------------------
    def test_Execute(self):
        assert self._InvokeAndCaptureKwargs(execute=True)[1]["execute"] is True

    # ----------------------------------------------------------------------
    def test_EvaluateAll(self):
        assert self._InvokeAndCaptureKwargs(evaluate_all=True)[1]["evaluate_all"] is True

    # ----------------------------------------------------------------------
    def test_NoResolution(self):
        kwargs = self._InvokeAndCaptureKwargs(display_resolution=False)[1]

        assert kwargs["display_resolution"] is False

    # ----------------------------------------------------------------------
    def test_NoRationale(self):
        kwargs = self._InvokeAndCaptureKwargs(display_rationale=False)[1]

        assert kwargs["display_rationale"] is False

    # ----------------------------------------------------------------------
    # The flags the caller ran with govern what the application displays.
    @pytest.mark.parametrize("flag", ["verbose", "debug"])
    def test_VerboseAndDebugAreTakenFromTheDoneManager(self, flag):
        assert self._InvokeAndCaptureKwargs(**{flag: True})[1][flag] is True
