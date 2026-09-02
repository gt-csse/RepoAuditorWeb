"""Renders EvaluateResults as the HTML fragment displayed by the web experience."""

import html

from dataclasses import dataclass
from typing import TYPE_CHECKING

from markdown_it import MarkdownIt

from RepoAuditorWeb.lib.requirement import EvaluateResultValue

if TYPE_CHECKING:
    from markdown_it.token import Token

    from RepoAuditorWeb.lib.requirement import EvaluateResult, Markdown


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Summary:
    """Counts of each result value produced by a run."""

    skipped: int = 0
    does_not_apply: int = 0
    success: int = 0
    warning: int = 0
    error: int = 0

    # ----------------------------------------------------------------------
    @classmethod
    def Create(cls, results: list[EvaluateResult]) -> Summary:
        """Tally the results by their result value."""

        counts = dict.fromkeys(_RESULT_VALUE_NAMES.values(), 0)

        for result in results:
            counts[_RESULT_VALUE_NAMES[result.result]] += 1

        return cls(**counts)

    # ----------------------------------------------------------------------
    @property
    def total(self) -> int:
        """The number of results tallied."""

        return self.skipped + self.does_not_apply + self.success + self.warning + self.error

    # ----------------------------------------------------------------------
    def CalcPercentage(self, count: int) -> str:
        """Format count as a percentage of the total."""

        if self.total == 0:
            return "0.00%"

        return f"{(count / self.total) * 100:.2f}%"


# ----------------------------------------------------------------------
def RenderResults(
    results: list[EvaluateResult],
    *,
    display_resolution: bool = True,
    display_rationale: bool = True,
    verbose: bool = False,
) -> str:
    """Render the results and their summary as an HTML fragment."""

    summary = Summary.Create(results)

    # Successful requirements are noise unless the user asked to see everything, matching what the
    # console experience displays.
    displayed = [
        result
        for result in results
        if verbose or result.result in {EvaluateResultValue.Warning, EvaluateResultValue.Error}
    ]

    return "".join(
        [
            _RenderSummary(summary),
            _RenderRequirements(
                displayed,
                display_resolution=display_resolution,
                display_rationale=display_rationale,
            ),
        ],
    )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_RESULT_VALUE_NAMES = {
    EvaluateResultValue.Skipped: "skipped",
    EvaluateResultValue.DoesNotApply: "does_not_apply",
    EvaluateResultValue.Success: "success",
    EvaluateResultValue.Warning: "warning",
    EvaluateResultValue.Error: "error",
}

_RESULT_VALUE_DISPLAY_NAMES = {
    EvaluateResultValue.Skipped: "Skipped",
    EvaluateResultValue.DoesNotApply: "Does Not Apply",
    EvaluateResultValue.Success: "Success",
    EvaluateResultValue.Warning: "Warning",
    EvaluateResultValue.Error: "Error",
}

_markdown = MarkdownIt("commonmark").enable("table")

# The requirement's name occupies 'h2' and the 'Resolution'/'Rationale' labels sit a level beneath
# it, so headings authored within the content are demoted to nest beneath them rather than compete
# with them.
_HEADING_OFFSET = 3
_MAX_HEADING_LEVEL = 6


# ----------------------------------------------------------------------
def _DemoteHeadings(tokens: list[Token]) -> None:
    for token in tokens:
        if token.type in {"heading_open", "heading_close"}:
            level = int(token.tag[1:]) + _HEADING_OFFSET
            token.tag = f"h{min(level, _MAX_HEADING_LEVEL)}"


# ----------------------------------------------------------------------
def _RenderSummary(summary: Summary) -> str:
    rows: list[str] = []

    for value, name in _RESULT_VALUE_NAMES.items():
        count = getattr(summary, name)

        rows.append(
            f'<tr class="{name}">'
            f"<th>{_RESULT_VALUE_DISPLAY_NAMES[value]}</th>"
            f"<td>{count}</td>"
            f"<td>{summary.CalcPercentage(count)}</td>"
            "</tr>",
        )

    return f'<table class="summary"><tbody>{"".join(rows)}</tbody></table>'


# ----------------------------------------------------------------------
def _RenderRequirements(
    results: list[EvaluateResult],
    *,
    display_resolution: bool,
    display_rationale: bool,
) -> str:
    sections: list[str] = []

    for result in results:
        name = _RESULT_VALUE_NAMES[result.result]

        # 'details' provides the collapsing behavior natively, so it remains keyboard accessible and
        # works before any script runs. It is open so that everything is visible by default.
        parts = [
            f'<details class="requirement {name}" open>',
            (
                f'<summary><span class="module">{html.escape(result.module.name)}</span>'
                f'Requirement <span class="name">{html.escape(result.requirement.name)}</span>'
                f'<span class="badge">{_RESULT_VALUE_DISPLAY_NAMES[result.result]}</span></summary>'
            ),
            '<div class="body">',
        ]

        if result.context:
            parts.append(f'<div class="context">{_RenderMarkdown(result.context)}</div>')

        for header, content in [
            ("Resolution", result.resolution if display_resolution else None),
            ("Rationale", result.rationale if display_rationale else None),
        ]:
            if not content:
                continue

            # Each section collapses independently of the requirement that encloses it and is open
            # so that everything is visible by default.
            parts.append(
                f'<details class="{header.lower()}" open><summary>{header}</summary>'
                f'<div class="content">{_RenderMarkdown(content)}</div></details>',
            )

        parts.append("</div></details>")

        sections.append("".join(parts))

    return "".join(sections)


# ----------------------------------------------------------------------
def _RenderMarkdown(content: Markdown) -> str:
    tokens = _markdown.parse(content)
    _DemoteHeadings(tokens)

    return _markdown.renderer.render(tokens, _markdown.options, {}).strip()
