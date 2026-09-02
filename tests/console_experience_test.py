import io
import textwrap

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from RepoAuditorWeb.console_experience import ExecuteExperience
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateRequirement(
    name: str = "MyRequirement",
    result: EvaluateResultValue = EvaluateResultValue.Success,
    context: str | None = None,
    resolution: str | None = None,
    rationale: str | None = None,
) -> MyRequirement:
    requirement = MyRequirement(name, "My requirement description.")
    requirement.evaluate_result = EvaluateResult(result, context, resolution, rationale, requirement)

    return requirement


# ----------------------------------------------------------------------
def _Execute(
    requirements: list[MyRequirement],
    *,
    verbose: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> str:
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", requirements, query_data={})])

    arguments: dict[str, dict[str | None, dict[str, object]]] = {
        "MyModule": {
            None: {"skip": False},
            **{requirement.name: {"skip": False} for requirement in requirements},
        },
    }

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...", flags=DoneManagerFlags.Create(verbose=verbose)) as dm:
        ExecuteExperience(
            dm,
            1234,
            "my_token",
            [module],
            arguments,
            display_resolution=display_resolution,
            display_rationale=display_rationale,
        )

    return sink.getvalue()


# ----------------------------------------------------------------------
def _GetSummary(output: str) -> str:
    # DoneManager indents its nested output and appends a 'DONE!' line, neither of which are
    # produced by the experience, so the five summary rows are isolated and the indentation that
    # DoneManager added is removed.
    lines = output.splitlines()

    index = next(index for index, line in enumerate(lines) if line.lstrip().startswith("Skipped:"))

    return textwrap.dedent("".join(f"{line}\n" for line in lines[index : index + 5]))


# ----------------------------------------------------------------------
class TestSummary:
    # ----------------------------------------------------------------------
    def test_NoResults(self):
        output = _Execute([])

        assert _GetSummary(output) == textwrap.dedent(
            """\
            Skipped:                0 [0.00%]
            Does Not Apply:         0 [0.00%]
            Success:                0 [0.00%]
            Warning:                0 [0.00%]
            Error:                  0 [0.00%]
            """,
        )

    # ----------------------------------------------------------------------
    def test_SingleResult(self):
        output = _Execute([_CreateRequirement()])

        assert _GetSummary(output) == textwrap.dedent(
            """\
            Skipped:                0 [0.00%]
            Does Not Apply:         0 [0.00%]
            Success:                1 [100.00%]
            Warning:                0 [0.00%]
            Error:                  0 [0.00%]
            """,
        )

    # ----------------------------------------------------------------------
    def test_AllResultValues(self):
        output = _Execute(
            [
                _CreateRequirement("Skipped", EvaluateResultValue.Skipped),
                _CreateRequirement("DoesNotApply", EvaluateResultValue.DoesNotApply),
                _CreateRequirement("Success", EvaluateResultValue.Success),
                _CreateRequirement("Warning", EvaluateResultValue.Warning),
                _CreateRequirement("Error", EvaluateResultValue.Error),
            ],
        )

        assert _GetSummary(output) == textwrap.dedent(
            """\
            Skipped:                1 [20.00%]
            Does Not Apply:         1 [20.00%]
            Success:                1 [20.00%]
            Warning:                1 [20.00%]
            Error:                  1 [20.00%]
            """,
        )

    # ----------------------------------------------------------------------
    def test_Percentages(self):
        output = _Execute(
            [
                _CreateRequirement("One", EvaluateResultValue.Success),
                _CreateRequirement("Two", EvaluateResultValue.Success),
                _CreateRequirement("Three", EvaluateResultValue.Error),
            ],
        )

        assert _GetSummary(output) == textwrap.dedent(
            """\
            Skipped:                0 [0.00%]
            Does Not Apply:         0 [0.00%]
            Success:                2 [66.67%]
            Warning:                0 [0.00%]
            Error:                  1 [33.33%]
            """,
        )


# ----------------------------------------------------------------------
class TestRequirementOutput:
    # ----------------------------------------------------------------------
    def test_SuccessIsNotDisplayed(self):
        output = _Execute([_CreateRequirement(context="My context.")])

        assert "Requirement 'MyRequirement'" not in output
        assert "My context." not in output

    # ----------------------------------------------------------------------
    def test_SkippedIsNotDisplayed(self):
        output = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.Skipped)])

        assert "Requirement 'MyRequirement'" not in output

    # ----------------------------------------------------------------------
    def test_DoesNotApplyIsNotDisplayed(self):
        output = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.DoesNotApply)])

        assert "Requirement 'MyRequirement'" not in output

    # ----------------------------------------------------------------------
    def test_Warning(self):
        output = _Execute(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.Warning, "My context.")],
        )

        assert "Requirement 'MyRequirement'" in output
        assert "=========================" in output
        assert "My context." in output

    # ----------------------------------------------------------------------
    def test_Error(self):
        output = _Execute(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.Error, "My context.")],
        )

        assert "Requirement 'MyRequirement'" in output
        assert "My context." in output

    # ----------------------------------------------------------------------
    # A result without context still produces the header so the requirement is identifiable.
    def test_NoContext(self):
        output = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.Error)])

        assert "Requirement 'MyRequirement'" in output

    # ----------------------------------------------------------------------
    def test_MultipleRequirementsAreDisplayed(self):
        output = _Execute(
            [
                _CreateRequirement("One", EvaluateResultValue.Error, "One context."),
                _CreateRequirement("Two", EvaluateResultValue.Success, "Two context."),
                _CreateRequirement("Three", EvaluateResultValue.Warning, "Three context."),
            ],
        )

        assert "Requirement 'One'" in output
        assert "One context." in output
        assert "Requirement 'Two'" not in output
        assert "Two context." not in output
        assert "Requirement 'Three'" in output
        assert "Three context." in output


# ----------------------------------------------------------------------
class TestVerbose:
    # ----------------------------------------------------------------------
    def test_SuccessIsDisplayed(self):
        output = _Execute(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.Success, "My context.")],
            verbose=True,
        )

        assert "Requirement 'MyRequirement'" in output
        assert "My context." in output

    # ----------------------------------------------------------------------
    def test_SkippedIsDisplayed(self):
        output = _Execute(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.Skipped)],
            verbose=True,
        )

        assert "Requirement 'MyRequirement'" in output

    # ----------------------------------------------------------------------
    def test_DoesNotApplyIsDisplayed(self):
        output = _Execute(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.DoesNotApply, "My context.")],
            verbose=True,
        )

        assert "Requirement 'MyRequirement'" in output
        assert "My context." in output


# ----------------------------------------------------------------------
class TestResolution:
    # ----------------------------------------------------------------------
    def test_Displayed(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="My resolution.",
                ),
            ],
        )

        assert "Resolution" in output
        assert "----------" in output
        assert "My resolution." in output

    # ----------------------------------------------------------------------
    def test_MultipleLines(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="Line one.\nLine two.",
                ),
            ],
        )

        assert "Line one." in output
        assert "Line two." in output

    # ----------------------------------------------------------------------
    def test_Suppressed(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="My resolution.",
                ),
            ],
            display_resolution=False,
        )

        assert "Resolution" not in output
        assert "My resolution." not in output

    # ----------------------------------------------------------------------
    # The header is only written when there is a resolution to display beneath it.
    def test_NoResolution(self):
        output = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.Error)])

        assert "Resolution" not in output


# ----------------------------------------------------------------------
class TestRationale:
    # ----------------------------------------------------------------------
    def test_Displayed(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    rationale="My rationale.",
                ),
            ],
        )

        assert "Rationale" in output
        assert "---------" in output
        assert "My rationale." in output

    # ----------------------------------------------------------------------
    def test_MultipleLines(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    rationale="Line one.\nLine two.",
                ),
            ],
        )

        assert "Line one." in output
        assert "Line two." in output

    # ----------------------------------------------------------------------
    def test_Suppressed(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    rationale="My rationale.",
                ),
            ],
            display_rationale=False,
        )

        assert "Rationale" not in output
        assert "My rationale." not in output

    # ----------------------------------------------------------------------
    def test_NoRationale(self):
        output = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.Error)])

        assert "Rationale" not in output


# ----------------------------------------------------------------------
class TestMarkdownRendering:
    # ----------------------------------------------------------------------
    # Urls must remain visible so that they survive redirection to a file.
    def test_HyperlinkUrlIsVisible(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="Visit [the settings page](https://github.com/o/r/settings).",
                ),
            ],
        )

        assert "the settings page (https://github.com/o/r/settings)" in output

    # ----------------------------------------------------------------------
    def test_TableIsRendered(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    context="| Setting | Value |\n| --- | --- |\n| signoff | missing |",
                ),
            ],
        )

        assert "Setting" in output
        assert "signoff" in output
        assert "─" in output

    # ----------------------------------------------------------------------
    # Bold names the control the user must interact with; quotes preserve that emphasis once the
    # styling that would have conveyed it is stripped for the console.
    def test_BoldIsQuoted(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="Check the **Settings** tab.",
                ),
            ],
        )

        assert 'Check the "Settings" tab.' in output
        assert "**Settings**" not in output

    # ----------------------------------------------------------------------
    def test_BoldWithinCodeSpanIsNotQuoted(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="Run `git config **x**` now.",
                ),
            ],
        )

        assert "Run git config **x** now." in output

    # ----------------------------------------------------------------------
    def test_BulletIsNotQuoted(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="- One item.\n- Two items.\n",
                ),
            ],
        )

        assert "• One item." in output
        assert '"•"' not in output
        assert '" • "' not in output

    # ----------------------------------------------------------------------
    # Requirements author steps as '1)'; the delimiter must survive rendering.
    def test_OrderedListDelimiterIsPreserved(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="1) First step.\n2) Second step.\n",
                ),
            ],
        )

        assert "1) First step." in output
        assert "2) Second step." in output

    # ----------------------------------------------------------------------
    def test_OrderedListPeriodDelimiterIsPreserved(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="1. First step.\n2. Second step.\n",
                ),
            ],
        )

        assert "1. First step." in output
        assert "2. Second step." in output

    # ----------------------------------------------------------------------
    # The prefix width accommodates the widest numeral so that content stays aligned.
    def test_OrderedListAlignsWiderNumerals(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="".join(f"{index}) Item.\n" for index in range(1, 11)),
                ),
            ],
        )

        assert "1)  Item." in output
        assert "10) Item." in output

    # ----------------------------------------------------------------------
    # rich pads each line to the console width; that padding must not reach the output.
    def test_NoTrailingWhitespace(self):
        output = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="A short line.",
                ),
            ],
        )

        assert "A short line." in output
        assert "A short line.  " not in output


# ----------------------------------------------------------------------
# The execution output produced by Execute is written before the summary.
def test_ExecutionOutputIsWritten():
    output = _Execute([_CreateRequirement()])

    assert "Executing module 'MyModule' (1 of 1)..." in output
    assert output.index("Executing module 'MyModule' (1 of 1)...") < output.index("Skipped:")
