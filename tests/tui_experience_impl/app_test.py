import threading

from unittest import mock

import pytest

from textual.containers import VerticalScroll
from textual.widgets import Button, Collapsible, Input, Label, RichLog, Select

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.requirement import EvaluateResultValue
from RepoAuditorWeb.tui_experience_impl.app import AuditorApp
from RepoAuditorWeb.tui_experience_impl.fields import CreateControlId

from conftest import EvaluateValues, MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateModule(
    *,
    parameters: dict[str, TyperParameter] | None = None,
    requirements: list[MyRequirement] | None = None,
) -> MyModule:
    if requirements is None:
        requirements = [MyRequirement("MyRequirement", "My requirement description.")]

    return MyModule(
        "MyModule",
        "My description.",
        [MyQuery("MyQuery", requirements, query_data={})],
        parameters={"url": TyperParameter(str, "https://example.com")} if parameters is None else parameters,
    )


# ----------------------------------------------------------------------
def _CreateApp(
    modules: list[Module] | None = None,
    arguments: dict[str, dict[str | None, dict[str, object]]] | None = None,
    **kwargs,
) -> AuditorApp:
    if modules is None:
        modules = [_CreateModule()]

    if arguments is None:
        arguments = {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}}

    return AuditorApp(modules, DynamicParameters(modules), arguments, **kwargs)


# ----------------------------------------------------------------------
async def _WaitForExecution(app: AuditorApp, pilot) -> None:
    """Wait for the run that is in flight to complete."""

    for _ in range(_MAX_PAUSES):
        if not app.is_executing:
            return

        await pilot.pause(_PAUSE_SECONDS)

    msg = "The execution did not complete."
    raise AssertionError(msg)


# ----------------------------------------------------------------------
def _EnumerateTitles(app: AuditorApp, class_name: str) -> list[str]:
    """Return the title of every Collapsible displayed under the named class."""

    return [collapsible.title for collapsible in app.query(Collapsible) if collapsible.has_class(class_name)]


# ----------------------------------------------------------------------
_MAX_PAUSES = 200

# A display large enough that the arguments and the results are each given a share of it.
_SIZE = (100, 40)
_PAUSE_SECONDS = 0.05


# ----------------------------------------------------------------------
class TestCompose:
    # ----------------------------------------------------------------------
    async def test_ModuleIsDisplayed(self):
        app = _CreateApp()

        async with app.run_test():
            titles = _EnumerateTitles(app, "group")

        assert titles == ["MyModule"]

    # ----------------------------------------------------------------------
    async def test_RequirementIsDisplayed(self):
        app = _CreateApp()

        async with app.run_test():
            titles = _EnumerateTitles(app, "section")

        assert titles == ["MyRequirement"]

    # ----------------------------------------------------------------------
    async def test_ParametersAreDisplayed(self):
        app = _CreateApp()

        async with app.run_test():
            control = app.query_one(f"#{CreateControlId('MyModule_url')}", Input)

            assert control.value == "https://example.com"

    # ----------------------------------------------------------------------
    # The values a run starts with are displayed for editing.
    async def test_ArgumentsAreDisplayed(self):
        app = _CreateApp(
            arguments={"MyModule": {None: {"url": "https://provided.example.com", "skip": False}}},
        )

        async with app.run_test():
            assert app.query_one(f"#{CreateControlId('MyModule_url')}", Input).value == (
                "https://provided.example.com"
            )

    # ----------------------------------------------------------------------
    # Nothing has been run yet, so the sections that report a run display nothing.
    async def test_OutputAndResultsAreHidden(self):
        app = _CreateApp()

        async with app.run_test():
            assert app.query_one("#output-section").has_class("hidden")
            assert app.query_one("#results-section").has_class("hidden")


# ----------------------------------------------------------------------
class TestCreateValues:
    # ----------------------------------------------------------------------
    async def test_ValuesAreCollected(self):
        app = _CreateApp()

        async with app.run_test():
            values = app.CreateValues()

        assert values == {
            "MyModule_skip": False,
            "MyModule_url": "https://example.com",
            "MyModule_MyRequirement_skip": False,
        }

    # ----------------------------------------------------------------------
    async def test_EditedValueIsCollected(self):
        app = _CreateApp()

        async with app.run_test():
            app.query_one(f"#{CreateControlId('MyModule_url')}", Input).value = "https://edited.example.com"

            assert app.CreateValues()["MyModule_url"] == "https://edited.example.com"

    # ----------------------------------------------------------------------
    # Whether a requirement runs and what it then expects are displayed as one control.
    async def test_RequirementModeIsCollected(self):
        requirement = MyRequirement(
            "ModeRequirement",
            "My requirement description.",
            parameters={
                "include": TyperParameter(bool, False),
                "require": TyperParameter(bool, False),
            },
        )

        app = _CreateApp(
            [_CreateModule(requirements=[requirement])],
            {"MyModule": {None: {"skip": False}}},
        )

        async with app.run_test():
            control = app.query_one(f"#{CreateControlId('MyModule_ModeRequirement_mode')}", Select)

            assert control.value == "skip"
            assert app.CreateValues()["MyModule_ModeRequirement_mode"] == "skip"


# ----------------------------------------------------------------------
class TestExecute:
    # ----------------------------------------------------------------------
    async def test_ResultsAreDisplayed(self):
        requirement = MyRequirement(
            "MyRequirement",
            "My requirement description.",
            evaluate_values=EvaluateValues(EvaluateResultValue.Error, "The context.", "Do this.", "Because."),
        )

        app = _CreateApp([_CreateModule(requirements=[requirement])])

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            titles = _EnumerateTitles(app, "requirement")

            assert titles == ["MyModule | Requirement 'MyRequirement' [Error]"]
            assert not app.query_one("#results-section").has_class("hidden")

    # ----------------------------------------------------------------------
    async def test_OutputIsDisplayed(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert not app.query_one("#output-section").has_class("hidden")
            assert len(app.query_one("#output", RichLog).lines) > 0

    # ----------------------------------------------------------------------
    async def test_StatusIsDisplayed(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert str(app.query_one("#status", Label).content) == "Execution completed."

    # ----------------------------------------------------------------------
    # A run that is underway leaves the control disabled so that a second run cannot interleave its
    # output into the log.
    async def test_ControlIsEnabledOnceTheRunCompletes(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert app.query_one("#execute", Button).disabled is False

    # ----------------------------------------------------------------------
    async def test_ASecondRunIsIgnoredWhileOneIsUnderway(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.is_executing = True
            app.ExecuteRequirements()

            # Nothing was run, so the section that reports a run displays nothing.
            assert app.query_one("#output-section").has_class("hidden")

            app.is_executing = False
            await pilot.pause()

    # ----------------------------------------------------------------------
    # The values the controls hold are what the run evaluates.
    async def test_EditedValuesAreUsed(self):
        module = _CreateModule()
        app = _CreateApp([module])

        async with app.run_test() as pilot:
            app.query_one(f"#{CreateControlId('MyModule_url')}", Input).value = "https://edited.example.com"

            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

        assert module.module_data_args is not None
        assert module.module_data_args[None]["url"] == "https://edited.example.com"

    # ----------------------------------------------------------------------
    # A widget may only be read by the thread that owns it, so the values are collected before the
    # run moves to a thread of its own.
    async def test_ValuesAreCollectedOnTheThreadThatOwnsTheControls(self):
        app = _CreateApp()

        threads: list[int | None] = []

        original = AuditorApp.CreateValues

        def CreateValues(self) -> dict[str, object]:
            threads.append(threading.current_thread().ident)

            return original(self)

        with mock.patch.object(AuditorApp, "CreateValues", CreateValues):
            async with app.run_test() as pilot:
                app.ExecuteRequirements()
                await _WaitForExecution(app, pilot)

        assert threads == [threading.main_thread().ident]

    # ----------------------------------------------------------------------
    async def test_EvaluateAllIsForwarded(self):
        requirement = MyRequirement("MyRequirement", "My requirement description.")
        app = _CreateApp([_CreateModule(requirements=[requirement])], evaluate_all=True)

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

        assert requirement.evaluate_all is True

    # ----------------------------------------------------------------------
    # Successful requirements are noise unless the user asked to see everything.
    async def test_SuccessIsDisplayedWhenVerbose(self):
        app = _CreateApp(verbose=True)

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            titles = _EnumerateTitles(app, "requirement")

        assert titles == ["MyModule | Requirement 'MyRequirement' [Success]"]

    # ----------------------------------------------------------------------
    async def test_SuccessIsNotDisplayed(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert _EnumerateTitles(app, "requirement") == []

    # ----------------------------------------------------------------------
    # A previous run's results are replaced rather than appended to.
    async def test_ResultsAreReplaced(self):
        requirement = MyRequirement(
            "MyRequirement",
            "My requirement description.",
            evaluate_values=EvaluateValues(EvaluateResultValue.Error),
        )

        app = _CreateApp([_CreateModule(requirements=[requirement])])

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert len(_EnumerateTitles(app, "requirement")) == 1

    # ----------------------------------------------------------------------
    # Automatic execution applies to the initial display.
    async def test_ExecuteOnStart(self):
        app = _CreateApp(execute=True)

        async with app.run_test() as pilot:
            await _WaitForExecution(app, pilot)

            assert not app.query_one("#output-section").has_class("hidden")

    # ----------------------------------------------------------------------
    async def test_NoExecuteOnStart(self):
        app = _CreateApp()

        async with app.run_test():
            assert app.query_one("#output-section").has_class("hidden")


# ----------------------------------------------------------------------
class TestLayout:
    # ----------------------------------------------------------------------
    @staticmethod
    def _CreateResultsApp() -> AuditorApp:
        # Enough failing requirements that what the results hold exceeds the space they are given.
        requirements = [
            MyRequirement(
                f"Requirement{index}",
                "My requirement description.",
                evaluate_values=EvaluateValues(
                    EvaluateResultValue.Error,
                    "The context.",
                    "Do this.",
                    "Because.",
                ),
            )
            for index in range(12)
        ]

        module = _CreateModule(requirements=requirements)

        return _CreateApp(
            [module],
            {
                "MyModule": {
                    None: {"skip": False},
                    **{requirement.name: {"skip": False} for requirement in requirements},
                },
            },
        )

    # ----------------------------------------------------------------------
    # The results are sized to the content they hold rather than to the section that displays them,
    # so that what does not fit is reached by scrolling rather than compressed away.
    async def test_ResultsScroll(self):
        app = self._CreateResultsApp()

        async with app.run_test(size=_SIZE) as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)
            await pilot.pause()

            section = app.query_one("#results-section", VerticalScroll)

            assert section.virtual_size.height > section.size.height
            assert section.max_scroll_y > 0

    # ----------------------------------------------------------------------
    async def test_ArgumentsAndResultsAreEqualInSize(self):
        app = self._CreateResultsApp()

        async with app.run_test(size=_SIZE) as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)
            await pilot.pause()

            arguments = app.query_one("#arguments", VerticalScroll)
            results = app.query_one("#results-section", VerticalScroll)

            assert arguments.size.height == results.size.height


# ----------------------------------------------------------------------
class TestExecuteErrors:
    # ----------------------------------------------------------------------
    # A module that raises is reported within the output, which Execute suppresses the exception to
    # produce, so the run itself still completes.
    async def test_ModuleErrorIsDisplayedInTheOutput(self):
        module = MyModule(
            "MyModule",
            "My description.",
            [MyQuery("MyQuery", [])],
            raise_exception=RuntimeError("My error."),
        )

        app = _CreateApp([module], {"MyModule": {None: {}}})

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            output = str(app.query_one("#output", RichLog).lines)

            assert "My error." in output
            assert str(app.query_one("#status", Label).content) == "Execution completed."

    # ----------------------------------------------------------------------
    # A value that cannot be coerced is reported in the output rather than out of the application.
    async def test_BadValueIsDisplayed(self):
        app = _CreateApp([_CreateModule(parameters={"count": TyperParameter(int, 1)})])

        async with app.run_test() as pilot:
            app.query_one(f"#{CreateControlId('MyModule_count')}", Input).value = "not a number"

            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert str(app.query_one("#status", Label).content) == "Execution failed."

    # ----------------------------------------------------------------------
    # The control is available again so that the user can correct what they entered.
    async def test_ControlIsEnabledAfterAnError(self):
        app = _CreateApp([_CreateModule(parameters={"count": TyperParameter(int, 1)})])

        async with app.run_test() as pilot:
            app.query_one(f"#{CreateControlId('MyModule_count')}", Input).value = "not a number"

            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            assert app.query_one("#execute", Button).disabled is False


# ----------------------------------------------------------------------
class TestReset:
    # ----------------------------------------------------------------------
    # Reset discards what a run produced, matching what the web experience discards.
    async def test_OutputAndResultsAreDiscarded(self):
        requirement = MyRequirement(
            "MyRequirement",
            "My requirement description.",
            evaluate_values=EvaluateValues(EvaluateResultValue.Error),
        )

        app = _CreateApp([_CreateModule(requirements=[requirement])])

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            app.ResetResults()
            await pilot.pause()

            assert app.query_one("#output-section").has_class("hidden")
            assert app.query_one("#results-section").has_class("hidden")
            assert _EnumerateTitles(app, "requirement") == []
            assert len(app.query_one("#output", RichLog).lines) == 0

    # ----------------------------------------------------------------------
    # What the user entered is retained so that a correction is made to it rather than to the values
    # the experience started with.
    async def test_EnteredValuesAreRetained(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.query_one(f"#{CreateControlId('MyModule_url')}", Input).value = "https://edited.example.com"

            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            app.ResetResults()
            await pilot.pause()

            assert app.query_one(f"#{CreateControlId('MyModule_url')}", Input).value == (
                "https://edited.example.com"
            )

    # ----------------------------------------------------------------------
    async def test_StatusIsCleared(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            app.ResetResults()
            await pilot.pause()

            assert str(app.query_one("#status", Label).content) == ""

    # ----------------------------------------------------------------------
    # A reset while a run is underway would discard the output the run is still writing.
    async def test_ResetIsIgnoredWhileARunIsUnderway(self):
        app = _CreateApp()

        async with app.run_test() as pilot:
            app.ExecuteRequirements()
            await _WaitForExecution(app, pilot)

            app.is_executing = True
            app.ResetResults()

            assert not app.query_one("#output-section").has_class("hidden")

            app.is_executing = False
            await pilot.pause()


# ----------------------------------------------------------------------
class TestActions:
    # ----------------------------------------------------------------------
    async def test_ExecuteButton(self):
        app = _CreateApp()

        with mock.patch.object(AuditorApp, "ExecuteRequirements") as execute_mock:
            async with app.run_test() as pilot:
                await pilot.click("#execute")

        assert execute_mock.call_count == 1

    # ----------------------------------------------------------------------
    async def test_ResetButton(self):
        app = _CreateApp()

        with mock.patch.object(AuditorApp, "ResetResults") as reset_mock:
            async with app.run_test() as pilot:
                await pilot.click("#reset")

        assert reset_mock.call_count == 1

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("key", "method"),
        [("f2", "ExecuteRequirements"), ("f3", "ResetResults")],
    )
    async def test_Binding(self, key, method):
        app = _CreateApp()

        with mock.patch.object(AuditorApp, method) as method_mock:
            async with app.run_test() as pilot:
                await pilot.press(key)

        assert method_mock.call_count == 1

    # ----------------------------------------------------------------------
    # An Input binds most of the control keys for editing, so the bindings are exercised while one
    # has focus to confirm that they are not shadowed by it.
    @pytest.mark.parametrize(
        ("key", "method"),
        [("f2", "ExecuteRequirements"), ("f3", "ResetResults")],
    )
    async def test_BindingWhileAnInputHasFocus(self, key, method):
        app = _CreateApp()

        with mock.patch.object(AuditorApp, method) as method_mock:
            async with app.run_test() as pilot:
                control = app.query_one(f"#{CreateControlId('MyModule_url')}", Input)
                control.focus()
                await pilot.pause()

                assert app.focused is control

                await pilot.press(key)

        assert method_mock.call_count == 1
