"""Renders EvaluateResults as the widgets displayed by the TUI experience."""

from typing import TYPE_CHECKING

from rich.table import Table
from textual.widgets import Collapsible, Markdown, Static

from RepoAuditorWeb.lib.requirement import EvaluateResultValue
from RepoAuditorWeb.lib.summary import RESULT_VALUE_NAMES, Summary

if TYPE_CHECKING:
    from collections.abc import Iterator

    from textual.widget import Widget

    from RepoAuditorWeb.lib.requirement import EvaluateResult


# ----------------------------------------------------------------------
RESULT_VALUE_DISPLAY_NAMES = {
    EvaluateResultValue.Skipped: "Skipped",
    EvaluateResultValue.DoesNotApply: "Does Not Apply",
    EvaluateResultValue.Success: "Success",
    EvaluateResultValue.Warning: "Warning",
    EvaluateResultValue.Error: "Error",
}


# ----------------------------------------------------------------------
def EnumerateResultWidgets(
    results: list[EvaluateResult],
    *,
    display_resolution: bool = True,
    display_rationale: bool = True,
    verbose: bool = False,
) -> Iterator[Widget]:
    """Yield the widgets that display the results and their summary."""

    yield CreateSummaryWidget(Summary.Create(results))

    # Successful requirements are noise unless the user asked to see everything, matching what the
    # console and web experiences display.
    for result in results:
        if not verbose and result.result not in {EvaluateResultValue.Warning, EvaluateResultValue.Error}:
            continue

        yield _CreateRequirementWidget(
            result,
            display_resolution=display_resolution,
            display_rationale=display_rationale,
        )


# ----------------------------------------------------------------------
def CreateSummaryWidget(summary: Summary) -> Static:
    """Create the widget that displays the counts of each result value."""

    table = Table(show_header=False, box=None, pad_edge=False)

    # The count is right-aligned so that the digits line up across rows.
    table.add_column("value")
    table.add_column("count", justify="right")
    table.add_column("percentage", justify="right")

    for value, name in RESULT_VALUE_NAMES.items():
        count = getattr(summary, name)

        table.add_row(
            RESULT_VALUE_DISPLAY_NAMES[value],
            str(count),
            summary.CalcPercentage(count),
            style=_RESULT_VALUE_STYLES[value],
        )

    return Static(table, classes="summary")


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# A result value is conveyed by color as well as by name, matching the web experience.
_RESULT_VALUE_STYLES = {
    EvaluateResultValue.Skipped: "dim",
    EvaluateResultValue.DoesNotApply: "dim",
    EvaluateResultValue.Success: "green",
    EvaluateResultValue.Warning: "yellow",
    EvaluateResultValue.Error: "red",
}


# ----------------------------------------------------------------------
def _CreateRequirementWidget(
    result: EvaluateResult,
    *,
    display_resolution: bool,
    display_rationale: bool,
) -> Widget:
    children: list[Widget] = []

    if result.context:
        children.append(Markdown(result.context, classes="context"))

    for header, content in [
        ("Resolution", result.resolution if display_resolution else None),
        ("Rationale", result.rationale if display_rationale else None),
    ]:
        if not content:
            continue

        # Each section collapses independently of the requirement that encloses it and is expanded
        # so that everything is visible by default.
        children.append(
            Collapsible(
                Markdown(content),
                title=header,
                collapsed=False,
                classes=header.lower(),
            ),
        )

    name = RESULT_VALUE_NAMES[result.result]

    return Collapsible(
        *children,
        title=(
            f"{result.module.name} | Requirement '{result.requirement.name}' "
            f"[{RESULT_VALUE_DISPLAY_NAMES[result.result]}]"
        ),
        collapsed=False,
        classes=f"requirement {name}",
    )
