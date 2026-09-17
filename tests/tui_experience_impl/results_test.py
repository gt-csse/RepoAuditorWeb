import io

from typing import cast

import pytest

from rich.console import Console
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import Collapsible, Markdown, Static

from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue
from RepoAuditorWeb.lib.summary import Summary
from RepoAuditorWeb.tui_experience_impl.results import CreateSummaryWidget, EnumerateResultWidgets

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateResult(
    result: EvaluateResultValue = EvaluateResultValue.Error,
    context: str | None = None,
    resolution: str | None = None,
    rationale: str | None = None,
    *,
    module_name: str = "MyModule",
    requirement_name: str = "MyRequirement",
) -> EvaluateResult:
    requirement = MyRequirement(requirement_name, "My requirement description.")
    module = MyModule(module_name, "My description.", [MyQuery("MyQuery", [requirement])])

    return EvaluateResult(result, context, resolution, rationale, requirement, module)


# ----------------------------------------------------------------------
def _RenderSummary(summary: Summary) -> str:
    sink = io.StringIO()

    Console(file=sink, width=80, no_color=True).print(CreateSummaryWidget(summary).content)

    return sink.getvalue()


# ----------------------------------------------------------------------
# A Collapsible holds its contents until it is mounted, so the widgets are displayed rather than
# inspected on their own.
class _ResultsApp(App):
    def __init__(self, widgets: list[Widget]) -> None:
        super().__init__()

        self.widgets = widgets

    def compose(self) -> ComposeResult:
        yield from self.widgets


# ----------------------------------------------------------------------
async def _MountRequirement(results: list[EvaluateResult], **kwargs) -> list[Collapsible]:
    """Display the widgets of a single result and return what its requirement encloses."""

    widgets = list(EnumerateResultWidgets(results, **kwargs))

    app = _ResultsApp(widgets)

    async with app.run_test():
        requirement = widgets[1]
        assert isinstance(requirement, Collapsible)

        # The widgets are unmounted once the application exits, so the contents are collected while
        # the requirement is still displayed.
        return _EnumerateContents(requirement)


# ----------------------------------------------------------------------
def _EnumerateContents(collapsible: Collapsible) -> list[Collapsible]:
    """Return what a mounted Collapsible displays, which its contents container encloses."""

    contents = next(child for child in collapsible.children if isinstance(child, Collapsible.Contents))

    return cast("list[Collapsible]", list(contents.children))


# ----------------------------------------------------------------------
class TestCreateSummaryWidget:
    # ----------------------------------------------------------------------
    def test_EveryResultValueIsDisplayed(self):
        output = _RenderSummary(Summary(skipped=1, does_not_apply=2, success=3, warning=4, error=5))

        for name in ["Skipped", "Does Not Apply", "Success", "Warning", "Error"]:
            assert name in output

    # ----------------------------------------------------------------------
    def test_CountsAndPercentagesAreDisplayed(self):
        output = _RenderSummary(Summary(success=1, error=3))

        assert "Success" in output
        assert "25.00%" in output
        assert "75.00%" in output

    # ----------------------------------------------------------------------
    # A run that evaluated nothing has no total to divide by.
    def test_NothingEvaluated(self):
        output = _RenderSummary(Summary())

        assert "0.00%" in output


# ----------------------------------------------------------------------
class TestEnumerateResultWidgets:
    # ----------------------------------------------------------------------
    @staticmethod
    def _CreateWidgets(results: list[EvaluateResult], **kwargs) -> list:
        return list(EnumerateResultWidgets(results, **kwargs))

    # ----------------------------------------------------------------------
    # The summary is displayed ahead of the requirements, matching the web experience.
    def test_SummaryIsFirst(self):
        widgets = self._CreateWidgets([])

        assert len(widgets) == 1
        assert isinstance(widgets[0], Static)

    # ----------------------------------------------------------------------
    def test_Error(self):
        widgets = self._CreateWidgets([_CreateResult(EvaluateResultValue.Error)])

        assert len(widgets) == 2

        requirement = widgets[1]

        assert isinstance(requirement, Collapsible)
        assert requirement.title == "MyModule | Requirement 'MyRequirement' [Error]"
        assert requirement.has_class("requirement")
        assert requirement.has_class("error")

    # ----------------------------------------------------------------------
    def test_Warning(self):
        requirement = self._CreateWidgets([_CreateResult(EvaluateResultValue.Warning)])[1]

        assert requirement.title == "MyModule | Requirement 'MyRequirement' [Warning]"
        assert requirement.has_class("warning")

    # ----------------------------------------------------------------------
    # Everything is visible by default rather than requiring the user to expand it.
    def test_RequirementsAreExpanded(self):
        assert self._CreateWidgets([_CreateResult()])[1].collapsed is False

    # ----------------------------------------------------------------------
    # Successful requirements are noise unless the user asked to see everything.
    def test_SuccessIsNotDisplayed(self):
        assert len(self._CreateWidgets([_CreateResult(EvaluateResultValue.Success)])) == 1

    # ----------------------------------------------------------------------
    def test_SkippedIsNotDisplayed(self):
        assert len(self._CreateWidgets([_CreateResult(EvaluateResultValue.Skipped)])) == 1

    # ----------------------------------------------------------------------
    def test_DoesNotApplyIsNotDisplayed(self):
        assert len(self._CreateWidgets([_CreateResult(EvaluateResultValue.DoesNotApply)])) == 1

    # ----------------------------------------------------------------------
    def test_SuccessIsDisplayedWhenVerbose(self):
        widgets = self._CreateWidgets([_CreateResult(EvaluateResultValue.Success)], verbose=True)

        assert len(widgets) == 2
        assert widgets[1].title == "MyModule | Requirement 'MyRequirement' [Success]"
        assert widgets[1].has_class("success")

    # ----------------------------------------------------------------------
    def test_DoesNotApplyIsDisplayedWhenVerbose(self):
        widgets = self._CreateWidgets([_CreateResult(EvaluateResultValue.DoesNotApply)], verbose=True)

        assert widgets[1].title == "MyModule | Requirement 'MyRequirement' [Does Not Apply]"
        assert widgets[1].has_class("does_not_apply")

    # ----------------------------------------------------------------------
    # Content is rendered as Markdown rather than as the source the requirement produced.
    @pytest.mark.asyncio
    async def test_Context(self):
        markdown = (await _MountRequirement([_CreateResult(context="The **context**.")]))[0]

        assert isinstance(markdown, Markdown)
        assert markdown.has_class("context")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Resolution(self):
        section = (await _MountRequirement([_CreateResult(resolution="Do this.")]))[0]

        assert isinstance(section, Collapsible)
        assert section.title == "Resolution"
        assert section.has_class("resolution")
        assert section.collapsed is False

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Rationale(self):
        section = (await _MountRequirement([_CreateResult(rationale="Because.")]))[0]

        assert isinstance(section, Collapsible)
        assert section.title == "Rationale"
        assert section.has_class("rationale")

    # ----------------------------------------------------------------------
    # The context is displayed ahead of the sections that explain what to do about it.
    @pytest.mark.asyncio
    async def test_ContextPrecedesTheSections(self):
        contents = await _MountRequirement(
            [_CreateResult(context="The context.", resolution="Do this.", rationale="Because.")],
        )

        assert isinstance(contents[0], Markdown)
        assert [child.title for child in contents[1:]] == ["Resolution", "Rationale"]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_NoResolution(self):
        contents = await _MountRequirement(
            [_CreateResult(resolution="Do this.", rationale="Because.")],
            display_resolution=False,
        )

        assert [child.title for child in contents] == ["Rationale"]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_NoRationale(self):
        contents = await _MountRequirement(
            [_CreateResult(resolution="Do this.", rationale="Because.")],
            display_rationale=False,
        )

        assert [child.title for child in contents] == ["Resolution"]

    # ----------------------------------------------------------------------
    # A requirement that produced no content displays its name and result alone.
    @pytest.mark.asyncio
    async def test_NoContent(self):
        assert await _MountRequirement([_CreateResult()]) == []

    # ----------------------------------------------------------------------
    def test_MultipleResults(self):
        widgets = self._CreateWidgets(
            [
                _CreateResult(EvaluateResultValue.Error, requirement_name="One"),
                _CreateResult(EvaluateResultValue.Warning, requirement_name="Two"),
            ],
        )

        assert [widget.title for widget in widgets[1:]] == [
            "MyModule | Requirement 'One' [Error]",
            "MyModule | Requirement 'Two' [Warning]",
        ]
