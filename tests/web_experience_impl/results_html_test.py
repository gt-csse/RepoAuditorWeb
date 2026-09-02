import pytest

from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue
from RepoAuditorWeb.web_experience_impl.results_html import RenderResults, Summary

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateResult(
    result: EvaluateResultValue = EvaluateResultValue.Error,
    module_name: str = "MyModule",
    requirement_name: str = "MyRequirement",
    resolution: str | None = None,
    rationale: str | None = None,
    context: str | None = None,
) -> EvaluateResult:
    requirement = MyRequirement(requirement_name, "My requirement description.")
    module = MyModule(module_name, "My description.", [MyQuery("MyQuery", [requirement])])

    return EvaluateResult(result, context, resolution, rationale, requirement, module)


# ----------------------------------------------------------------------
# The module is rendered alongside the requirement so that the source of each result is clear.
def test_ModuleIsRendered():
    html = RenderResults([_CreateResult()])

    assert '<span class="module">MyModule</span>' in html
    assert '<span class="name">MyRequirement</span>' in html


# ----------------------------------------------------------------------
def test_ModuleIsRenderedForEachResult():
    html = RenderResults(
        [
            _CreateResult(module_name="First", requirement_name="One"),
            _CreateResult(module_name="Second", requirement_name="Two"),
        ],
    )

    assert '<span class="module">First</span>' in html
    assert '<span class="module">Second</span>' in html


# ----------------------------------------------------------------------
# A module name is escaped so that it cannot alter the surrounding markup.
def test_ModuleNameIsEscaped():
    html = RenderResults([_CreateResult(module_name="<script>")])

    assert '<span class="module">&lt;script&gt;</span>' in html
    assert "<script>" not in html


# ----------------------------------------------------------------------
# Successful results are only rendered when everything was requested, so the module accompanies
# them only then.
def test_ModuleIsRenderedWhenVerbose():
    results = [_CreateResult(EvaluateResultValue.Success)]

    assert '<span class="module">MyModule</span>' not in RenderResults(results)
    assert '<span class="module">MyModule</span>' in RenderResults(results, verbose=True)


# ----------------------------------------------------------------------
# Each section collapses on its own and starts expanded.
def test_SectionsAreCollapsibleAndOpen():
    html = RenderResults(
        [_CreateResult(resolution="Do this.", rationale="Because of that.")],
    )

    assert '<details class="resolution" open><summary>Resolution</summary>' in html
    assert '<details class="rationale" open><summary>Rationale</summary>' in html


# ----------------------------------------------------------------------
def test_SectionsAreOmittedWhenNotDisplayed():
    results = [_CreateResult(resolution="Do this.", rationale="Because of that.")]

    html = RenderResults(results, display_resolution=False, display_rationale=False)

    assert 'class="resolution"' not in html
    assert 'class="rationale"' not in html


# ----------------------------------------------------------------------
def test_SectionsAreOmittedWhenEmpty():
    html = RenderResults([_CreateResult()])

    assert 'class="resolution"' not in html
    assert 'class="rationale"' not in html


# ----------------------------------------------------------------------
class TestContext:
    # ----------------------------------------------------------------------
    def test_ContextIsRendered(self):
        html = RenderResults([_CreateResult(context="The value is `10`.")])

        assert '<div class="context"><p>The value is <code>10</code>.</p></div>' in html

    # ----------------------------------------------------------------------
    def test_ContextIsOmittedWhenEmpty(self):
        assert 'class="context"' not in RenderResults([_CreateResult()])


# ----------------------------------------------------------------------
# The requirement's name occupies 'h2' and the section labels sit beneath it, so headings authored
# within the content are demoted rather than competing with them.
class TestHeadings:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("authored", "expected"),
        [(1, 4), (2, 5), (3, 6)],
    )
    def test_HeadingsAreDemoted(self, authored, expected):
        html = RenderResults([_CreateResult(context=f"{'#' * authored} Heading")])

        assert f"<h{expected}>Heading</h{expected}>" in html

    # ----------------------------------------------------------------------
    # There is no heading beyond 'h6', so deeper headings are clamped to it.
    @pytest.mark.parametrize("authored", [4, 5, 6])
    def test_HeadingsAreClamped(self, authored):
        html = RenderResults([_CreateResult(context=f"{'#' * authored} Heading")])

        assert "<h6>Heading</h6>" in html


# ----------------------------------------------------------------------
class TestSummary:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        summary = Summary.Create([])

        assert summary == Summary()
        assert summary.total == 0

    # ----------------------------------------------------------------------
    def test_Counts(self):
        summary = Summary.Create(
            [
                _CreateResult(EvaluateResultValue.Skipped),
                _CreateResult(EvaluateResultValue.DoesNotApply),
                _CreateResult(EvaluateResultValue.Success),
                _CreateResult(EvaluateResultValue.Success),
                _CreateResult(EvaluateResultValue.Warning),
                _CreateResult(EvaluateResultValue.Error),
            ],
        )

        assert summary == Summary(skipped=1, does_not_apply=1, success=2, warning=1, error=1)
        assert summary.total == 6

    # ----------------------------------------------------------------------
    def test_CalcPercentage(self):
        assert Summary.Create([_CreateResult()] * 4).CalcPercentage(1) == "25.00%"

    # ----------------------------------------------------------------------
    # Nothing was tallied, so there is no total to divide by.
    def test_CalcPercentageWithoutResults(self):
        assert Summary().CalcPercentage(0) == "0.00%"

    # ----------------------------------------------------------------------
    # The summary is rendered even when nothing ran so that the page is not blank.
    def test_TableIsRenderedWithoutResults(self):
        html = RenderResults([])

        for name in ["skipped", "does_not_apply", "success", "warning", "error"]:
            assert f'<tr class="{name}"><th>' in html

        assert html.count("<td>0.00%</td>") == 5

    # ----------------------------------------------------------------------
    def test_TableIsRendered(self):
        html = RenderResults([_CreateResult(EvaluateResultValue.Error)])

        assert '<tr class="error"><th>Error</th><td>1</td><td>100.00%</td></tr>' in html
        assert '<tr class="success"><th>Success</th><td>0</td><td>0.00%</td></tr>' in html

    # ----------------------------------------------------------------------
    # Results that are not displayed are still tallied so that the summary reflects the whole run.
    def test_ResultsThatAreNotDisplayedAreTallied(self):
        html = RenderResults([_CreateResult(EvaluateResultValue.Success)])

        assert '<tr class="success"><th>Success</th><td>1</td><td>100.00%</td></tr>' in html
        assert 'class="requirement' not in html
