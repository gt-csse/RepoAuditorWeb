import io
import json
import textwrap

from contextlib import redirect_stdout

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from RepoAuditorWeb.json_experience import ExecuteExperience
from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
from RepoAuditorWeb.lib.requirement import EvaluateResultValue

from conftest import EvaluateValues, MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateRequirement(
    name: str = "MyRequirement",
    result: EvaluateResultValue = EvaluateResultValue.Success,
    context: str | None = None,
    resolution: str | None = None,
    rationale: str | None = None,
) -> MyRequirement:
    return MyRequirement(
        name,
        "My requirement description.",
        evaluate_values=EvaluateValues(result, context, resolution, rationale),
    )


# ----------------------------------------------------------------------
def _ExecuteRaw(
    requirements: list[MyRequirement],
    *,
    verbose: bool = False,
    evaluate_all: bool = False,
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

    # The document is written to stdout while DoneManager writes elsewhere, so the two are captured
    # separately here just as they are separated on the command line.
    progress = io.StringIO()
    document = io.StringIO()

    with (
        DoneManager.Create(progress, "Testing...", flags=DoneManagerFlags.Create(verbose=verbose)) as dm,
        redirect_stdout(document),
    ):
        ExecuteExperience(
            dm,
            1234,
            "my_token",
            [module],
            DynamicParameters([module]),
            arguments,
            evaluate_all=evaluate_all,
            display_resolution=display_resolution,
            display_rationale=display_rationale,
        )

    return document.getvalue()


# ----------------------------------------------------------------------
def _Execute(requirements: list[MyRequirement], **kwargs) -> dict:
    return json.loads(_ExecuteRaw(requirements, **kwargs))


# ----------------------------------------------------------------------
class TestSummary:
    # ----------------------------------------------------------------------
    def test_NoResults(self):
        assert _Execute([])["summary"] == {
            "skipped": 0,
            "does_not_apply": 0,
            "success": 0,
            "warning": 0,
            "error": 0,
            "total": 0,
        }

    # ----------------------------------------------------------------------
    def test_SingleResult(self):
        assert _Execute([_CreateRequirement()])["summary"] == {
            "skipped": 0,
            "does_not_apply": 0,
            "success": 1,
            "warning": 0,
            "error": 0,
            "total": 1,
        }

    # ----------------------------------------------------------------------
    def test_AllResultValues(self):
        assert _Execute(
            [
                _CreateRequirement("Skipped", EvaluateResultValue.Skipped),
                _CreateRequirement("DoesNotApply", EvaluateResultValue.DoesNotApply),
                _CreateRequirement("Success", EvaluateResultValue.Success),
                _CreateRequirement("Warning", EvaluateResultValue.Warning),
                _CreateRequirement("Error", EvaluateResultValue.Error),
            ],
        )["summary"] == {
            "skipped": 1,
            "does_not_apply": 1,
            "success": 1,
            "warning": 1,
            "error": 1,
            "total": 5,
        }


# ----------------------------------------------------------------------
class TestResults:
    # ----------------------------------------------------------------------
    def test_NoResults(self):
        assert _Execute([])["results"] == []

    # ----------------------------------------------------------------------
    def test_Result(self):
        assert _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    context="My context.",
                    resolution="My resolution.",
                    rationale="My rationale.",
                ),
            ],
        )["results"] == [
            {
                "module": "MyModule",
                "requirement": "MyRequirement",
                "description": "My requirement description.",
                "result": "error",
                "context": "My context.",
                "resolution": "My resolution.",
                "rationale": "My rationale.",
            },
        ]

    # ----------------------------------------------------------------------
    # Content that was not produced is reported as null rather than omitted, so that a consumer can
    # read every key without testing for its presence.
    def test_NoContent(self):
        result = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.Error)])["results"][0]

        assert result["context"] is None
        assert result["resolution"] is None
        assert result["rationale"] is None

    # ----------------------------------------------------------------------
    def test_ResultValueNames(self):
        results = _Execute(
            [
                _CreateRequirement("Skipped", EvaluateResultValue.Skipped),
                _CreateRequirement("DoesNotApply", EvaluateResultValue.DoesNotApply),
                _CreateRequirement("Success", EvaluateResultValue.Success),
                _CreateRequirement("Warning", EvaluateResultValue.Warning),
                _CreateRequirement("Error", EvaluateResultValue.Error),
            ],
        )["results"]

        assert [result["result"] for result in results] == [
            "skipped",
            "does_not_apply",
            "success",
            "warning",
            "error",
        ]

    # ----------------------------------------------------------------------
    # The other experiences display failures only; the document reports everything so that the
    # consumer filters it according to its own needs.
    def test_SuccessIsReported(self):
        results = _Execute([_CreateRequirement("MyRequirement", EvaluateResultValue.Success)])["results"]

        assert len(results) == 1
        assert results[0]["requirement"] == "MyRequirement"

    # ----------------------------------------------------------------------
    def test_MultipleResultsRetainOrder(self):
        results = _Execute(
            [
                _CreateRequirement("One"),
                _CreateRequirement("Two"),
                _CreateRequirement("Three"),
            ],
        )["results"]

        assert [result["requirement"] for result in results] == ["One", "Two", "Three"]

    # ----------------------------------------------------------------------
    # Markdown is the authored form of the content, so it is reported unaltered and the consumer
    # decides how to render it.
    def test_MarkdownIsNotRendered(self):
        result = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="Check the **Settings** tab at [the page](https://example.com).",
                ),
            ],
        )["results"][0]

        assert result["resolution"] == "Check the **Settings** tab at [the page](https://example.com)."


# ----------------------------------------------------------------------
class TestDisplayFlags:
    # ----------------------------------------------------------------------
    def test_ResolutionIsSuppressed(self):
        result = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="My resolution.",
                    rationale="My rationale.",
                ),
            ],
            display_resolution=False,
        )["results"][0]

        assert result["resolution"] is None
        assert result["rationale"] == "My rationale."

    # ----------------------------------------------------------------------
    def test_RationaleIsSuppressed(self):
        result = _Execute(
            [
                _CreateRequirement(
                    "MyRequirement",
                    EvaluateResultValue.Error,
                    resolution="My resolution.",
                    rationale="My rationale.",
                ),
            ],
            display_rationale=False,
        )["results"][0]

        assert result["resolution"] == "My resolution."
        assert result["rationale"] is None


# ----------------------------------------------------------------------
# Verbose output is a display concern of the other experiences; the document reports every result
# regardless of it.
class TestVerbose:
    # ----------------------------------------------------------------------
    def test_DocumentIsUnchanged(self):
        def CreateRequirements() -> list[MyRequirement]:
            return [
                _CreateRequirement("Success", EvaluateResultValue.Success, context="My context."),
                _CreateRequirement("Error", EvaluateResultValue.Error, context="My context."),
            ]

        assert _ExecuteRaw(CreateRequirements(), verbose=True) == _ExecuteRaw(CreateRequirements())


# ----------------------------------------------------------------------
class TestEvaluateAll:
    # ----------------------------------------------------------------------
    def test_NotForwardedByDefault(self):
        requirement = _CreateRequirement()

        _Execute([requirement])

        assert requirement.evaluate_all is False

    # ----------------------------------------------------------------------
    def test_Forwarded(self):
        requirement = _CreateRequirement()

        _Execute([requirement], evaluate_all=True)

        assert requirement.evaluate_all is True


# ----------------------------------------------------------------------
class TestSchemaVersion:
    # ----------------------------------------------------------------------
    # A consumer reads the version to decide whether it understands the document.
    def test_Reported(self):
        assert _Execute([])["schema_version"] == 1

    # ----------------------------------------------------------------------
    def test_ReportedWithResults(self):
        assert _Execute([_CreateRequirement()])["schema_version"] == 1


# ----------------------------------------------------------------------
class TestDocument:
    # ----------------------------------------------------------------------
    # The document is indented so that it remains readable when it is displayed rather than piped.
    def test_Content(self):
        assert _ExecuteRaw(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.Error, context="My context.")],
        ) == textwrap.dedent(
            """\
            {
              "schema_version": 1,
              "summary": {
                "skipped": 0,
                "does_not_apply": 0,
                "success": 0,
                "warning": 0,
                "error": 1,
                "total": 1
              },
              "results": [
                {
                  "module": "MyModule",
                  "requirement": "MyRequirement",
                  "description": "My requirement description.",
                  "result": "error",
                  "context": "My context.",
                  "resolution": null,
                  "rationale": null
                }
              ]
            }
            """,
        )

    # ----------------------------------------------------------------------
    # The document is written to stdout alone; nothing that DoneManager produces reaches it.
    def test_ProgressIsExcluded(self):
        document = _ExecuteRaw([_CreateRequirement()])

        assert "Executing module" not in document
        assert "DONE!" not in document
