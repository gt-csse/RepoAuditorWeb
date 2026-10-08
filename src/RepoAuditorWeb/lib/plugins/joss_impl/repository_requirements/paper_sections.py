import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_content_requirement import (
    PaperContentRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper


# ----------------------------------------------------------------------
class PaperSectionsRequirement(PaperContentRequirement):
    """Validates that the paper contains the sections that JOSS requires."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PaperSections",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require the sections that JOSS requires: Summary, Statement of
                need, State of the field, Software design, Research impact statement, and AI usage
                disclosure.

                ## Reasons for this Default

                - The JOSS review checklist asks reviewers to confirm that each of these sections is
                  present, and a paper missing any of them will be returned to the authors.

                ## Reasons to Override this Default

                - JOSS has changed the sections that it requires (`--JOSS-PaperSections-sections`).
                - The software is not being prepared for submission to JOSS.
                """,
            ),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "sections": TyperParameter(
                list[str],
                [
                    "Summary",
                    "Statement of need",
                    "State of the field",
                    "Software design",
                    "Research impact statement",
                    "AI usage disclosure",
                ],
                OptionInfo(help="Headings that must be present in the paper (case-insensitive)."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluatePaper(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        paper: Paper,
    ) -> EvaluateResult:
        headings = {" ".join(heading.split()).casefold() for heading in paper.headings}
        missing = [
            section
            for section in cast(list[str], requirement_data["sections"])
            if " ".join(section.split()).casefold() not in headings
        ]

        if missing:
            missing_str = ", ".join(f"`{section}`" for section in missing)

            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"`{paper.path}` does not contain these sections: {missing_str}.",
                textwrap.dedent(
                    f"""\
                    Add a heading for each missing section to `{paper.path}` (for example, `# {missing[0]}`).
                    See [What should my paper contain?](https://joss.readthedocs.io/en/latest/paper.html#what-should-my-paper-contain)
                    for a description of each section.
                    """,
                ),
            )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Success,
            f"`{paper.path}` contains all of the required sections.",
        )
