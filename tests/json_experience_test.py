import io
import json
import textwrap

from contextlib import nullcontext, redirect_stderr, redirect_stdout
from unittest import mock

import pytest

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from RepoAuditorWeb.json_experience import CreateRepositoryEntry, ExecuteExperience
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
def _ExecuteWithOutput(
    requirements: list[MyRequirement],
    *,
    common_arguments: dict[str, object] | None = None,
    verbose: bool = False,
    evaluate_all: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
    urls: list[str | None] | None = None,
    expected_exception: type[BaseException] | None = None,
) -> tuple[str, str]:
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", requirements, query_data={})])

    arguments: dict[str, dict[str | None, dict[str, object]]] = {
        "MyModule": {
            None: {"skip": False},
            **{requirement.name: {"skip": False} for requirement in requirements},
        },
    }

    # DoneManager writes elsewhere, so anything written to stdout or stderr came from the experience
    # itself.
    progress = io.StringIO()
    output = io.StringIO()
    status = io.StringIO()

    with (
        DoneManager.Create(progress, "Testing...", flags=DoneManagerFlags.Create(verbose=verbose)) as dm,
        redirect_stdout(output),
        redirect_stderr(status),
        pytest.raises(expected_exception) if expected_exception is not None else nullcontext(),
    ):
        ExecuteExperience(
            dm,
            1234,
            "my_token",
            [module],
            DynamicParameters([module]),
            arguments,
            {} if common_arguments is None else common_arguments,
            [None] if urls is None else urls,
            evaluate_all=evaluate_all,
            display_resolution=display_resolution,
            display_rationale=display_rationale,
        )

    return output.getvalue(), status.getvalue()


# ----------------------------------------------------------------------
def _ExecuteDocument(requirements: list[MyRequirement], **kwargs) -> dict:
    return json.loads(_ExecuteWithOutput(requirements, **kwargs)[0])


# ----------------------------------------------------------------------
def _Execute(requirements: list[MyRequirement], **kwargs) -> dict:
    repositories = _ExecuteDocument(requirements, **kwargs)["repositories"]

    assert len(repositories) == 1

    return repositories[0]


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

        assert _Execute(CreateRequirements(), verbose=True) == _Execute(CreateRequirements())


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
class TestArguments:
    # ----------------------------------------------------------------------
    # Module and requirement arguments are separated rather than keyed by null, which JSON objects do
    # not support.
    def test_Arguments(self):
        assert _Execute([_CreateRequirement("MyRequirement")])["arguments"] == {
            "MyModule": {
                "module": {"skip": False},
                "requirements": {"MyRequirement": {"skip": False}},
            },
        }

    # ----------------------------------------------------------------------
    def test_CommonArguments(self):
        assert _Execute(
            [],
            common_arguments={"pat": None, "branch": "main"},
            urls=["https://github.com/gt-csse/RepoAuditorWeb"],
        )["common_arguments"] == {
            "url": "https://github.com/gt-csse/RepoAuditorWeb",
            "pat": None,
            "branch": "main",
        }

    # ----------------------------------------------------------------------
    # The document may be shared, so the PAT is never included.
    def test_PatIsRedacted(self):
        assert _Execute([], common_arguments={"pat": "my_pat"})["common_arguments"] == {
            "url": None,
            "pat": "***",
        }


# ----------------------------------------------------------------------
class TestRepositories:
    # ----------------------------------------------------------------------
    def test_EntryForEachRepository(self):
        document = _ExecuteDocument([_CreateRequirement()], urls=["first_url", "second_url"])

        assert [repository["common_arguments"] for repository in document["repositories"]] == [
            {"url": "first_url"},
            {"url": "second_url"},
        ]

    # ----------------------------------------------------------------------
    # A failure while auditing one repository is recorded in its entry and does not prevent the others
    # from being audited.
    def test_RepositoryError(self):
        with mock.patch(
            "RepoAuditorWeb.json_experience.Execute",
            side_effect=[RuntimeError("My error."), []],
        ):
            document = _ExecuteDocument([], urls=["first_url", "second_url"])

        repositories = document["repositories"]

        assert document["error"] is None
        assert len(repositories) == 2
        assert repositories[0]["error"] == "My error."
        assert repositories[0]["results"] is None
        assert repositories[1]["error"] is None
        assert repositories[1]["results"] == []


# ----------------------------------------------------------------------
class TestCreateRepositoryEntry:
    # ----------------------------------------------------------------------
    # A repository whose audit could not run is still reported, so that it does not silently
    # disappear from the document.
    def test_Error(self):
        assert CreateRepositoryEntry(
            {"MyModule": {None: {"skip": False}}},
            {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": "my_pat"},
            error="My error.",
        ) == {
            "arguments": {"MyModule": {"module": {"skip": False}, "requirements": {}}},
            "common_arguments": {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": "***"},
            "error": "My error.",
            "summary": None,
            "results": None,
        }


# ----------------------------------------------------------------------
class TestDocument:
    # ----------------------------------------------------------------------
    # The document is indented so that it remains readable when it is displayed rather than piped.
    def test_Content(self):
        output, _ = _ExecuteWithOutput(
            [_CreateRequirement("MyRequirement", EvaluateResultValue.Error, context="My context.")]
        )

        assert output == textwrap.dedent(
            """            {
              "schema_version": 2,
              "error": null,
              "repositories": [
                {
                  "arguments": {
                    "MyModule": {
                      "module": {
                        "skip": false
                      },
                      "requirements": {
                        "MyRequirement": {
                          "skip": false
                        }
                      }
                    }
                  },
                  "common_arguments": {
                    "url": null
                  },
                  "error": null,
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
              ]
            }
            """,
        )

    # ----------------------------------------------------------------------
    # The status output is written to stderr, so a blank line separates it from the document when
    # both are displayed together.
    def test_StatusOutputSeparator(self):
        assert _ExecuteWithOutput([_CreateRequirement()])[1] == "\n"

    # ----------------------------------------------------------------------
    # The document is valid however the run ends, so that a consumer can always parse it.
    def test_Error(self):
        with mock.patch(
            "RepoAuditorWeb.json_experience.InvokeForEachRepository",
            side_effect=RuntimeError("My error."),
        ):
            document = _ExecuteDocument([], expected_exception=RuntimeError)

        assert document == {"schema_version": 2, "error": "My error.", "repositories": []}

    # ----------------------------------------------------------------------
    # Repositories audited before the run was interrupted are retained in the document.
    def test_Interrupted(self):
        with mock.patch(
            "RepoAuditorWeb.json_experience.Execute",
            side_effect=[[], KeyboardInterrupt],
        ):
            document = _ExecuteDocument(
                [],
                urls=["first_url", "second_url"],
                expected_exception=KeyboardInterrupt,
            )

        assert document["error"] == "The run was interrupted."
        assert [repository["common_arguments"] for repository in document["repositories"]] == [
            {"url": "first_url"},
        ]
