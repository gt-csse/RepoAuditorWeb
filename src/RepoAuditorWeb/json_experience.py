import json
import sys

from dataclasses import asdict
from typing import TYPE_CHECKING

from RepoAuditorWeb.lib.execute import Execute
from RepoAuditorWeb.lib.summary import RESULT_VALUE_NAMES, Summary

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.requirement import EvaluateResult


# ----------------------------------------------------------------------
def ExecuteExperience(  # noqa: PLR0913
    dm: DoneManager,
    port: int,  # noqa: ARG001
    token: str,  # noqa: ARG001
    modules: list[Module],
    dynamic_parameters: DynamicParameters,  # noqa: ARG001
    arguments: dict[str, dict[str | None, dict[str, object]]],
    common_arguments: dict[str, object],
    *,
    execute: bool = False,  # noqa: ARG001
    evaluate_all: bool = False,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> dict[str, object]:
    """Execute the application in a json experience, returning the repository's entry in the document."""

    # The json experience has no control to invoke, so `execute` is implied.

    results = Execute(dm, modules, arguments, common_arguments, evaluate_all=evaluate_all)

    return CreateRepositoryEntry(
        arguments,
        common_arguments,
        results=results,
        display_resolution=display_resolution,
        display_rationale=display_rationale,
    )


# ----------------------------------------------------------------------
def CreateRepositoryEntry(
    arguments: dict[str, dict[str | None, dict[str, object]]],
    common_arguments: dict[str, object],
    *,
    results: list[EvaluateResult] | None = None,
    error: str | None = None,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> dict[str, object]:
    """Create the document's entry for a repository, which has either results or an error."""

    assert (results is None) != (error is None), (results, error)

    return {
        "arguments": {
            module_name: {
                "module": module_arguments.get(None, {}),
                "requirements": {
                    requirement_name: requirement_arguments
                    for requirement_name, requirement_arguments in module_arguments.items()
                    if requirement_name is not None
                },
            }
            for module_name, module_arguments in arguments.items()
        },
        # The document is written where it may be shared, so the PAT is never included.
        "common_arguments": {
            **common_arguments,
            **({"pat": _REDACTED} if common_arguments.get("pat") else {}),
        },
        "error": error,
        "summary": None if results is None else _CreateSummary(results),
        "results": None
        if results is None
        else [
            _CreateResult(
                result,
                display_resolution=display_resolution,
                display_rationale=display_rationale,
            )
            for result in results
        ],
    }


# ----------------------------------------------------------------------
def WriteDocument(repositories: list[dict[str, object]], error: str | None) -> None:
    """Write the document for a run, which is valid however the run ended."""

    # The document is the only thing written to stdout (everything that DoneManager produces is
    # written to stderr), so it can be redirected to a file or piped to another process as-is.
    json.dump(
        {
            "schema_version": _SCHEMA_VERSION,
            "error": error,
            "repositories": repositories,
        },
        sys.stdout,
        indent=_INDENT,
    )

    sys.stdout.write("\n")


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_INDENT = 2

# Incremented whenever a change to the document would break a consumer that reads it, so that the
# consumer can detect the change rather than misinterpret the content.
_SCHEMA_VERSION = 2

_REDACTED = "***"


# ----------------------------------------------------------------------
def _CreateSummary(results: list[EvaluateResult]) -> dict[str, int]:
    summary = Summary.Create(results)

    # The total is derived rather than tallied, but including it spares every consumer from summing
    # the counts itself.
    return {**asdict(summary), "total": summary.total}


# ----------------------------------------------------------------------
def _CreateResult(
    result: EvaluateResult,
    *,
    display_resolution: bool,
    display_rationale: bool,
) -> dict[str, object]:
    # Every result is reported, rather than only the failures that the other experiences display,
    # because the consumer of the document filters it according to its own needs. Content remains
    # Markdown so that the consumer decides how to render it.
    return {
        "module": result.module.name,
        "requirement": result.requirement.name,
        "description": result.requirement.description,
        "result": RESULT_VALUE_NAMES[result.result],
        "context": result.context,
        "resolution": result.resolution if display_resolution else None,
        "rationale": result.rationale if display_rationale else None,
    }
