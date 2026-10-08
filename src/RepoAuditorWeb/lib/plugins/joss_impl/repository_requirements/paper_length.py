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
class PaperLengthRequirement(PaperContentRequirement):
    """Validates that the number of words in the paper is within the range that JOSS recommends."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PaperLength",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require between 750 and 1750 words, excluding the metadata.

                ## Reasons for this Default

                - JOSS states that the paper should be between 750 and 1750 words, and that authors of
                  significantly longer papers may be asked to reduce their length.
                - JOSS papers are intentionally short; API documentation and other detailed content belong
                  in the software's documentation rather than in the paper.

                ## Reasons to Override this Default

                - The paper contains content that inflates the word count, such as tables, equations, or
                  code (`--JOSS-PaperLength-maximum`).
                - The software is not being prepared for submission to JOSS.
                """,
            ),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "minimum": TyperParameter(int, 750, OptionInfo(help="Minimum number of words.")),
            "maximum": TyperParameter(int, 1750, OptionInfo(help="Maximum number of words.")),
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
        minimum = cast(int, requirement_data["minimum"])
        maximum = cast(int, requirement_data["maximum"])

        word_count = len(paper.text.split())
        context = f"`{paper.path}` contains {word_count} words"

        if word_count < minimum:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"{context}, but at least {minimum} are required.",
                "Expand the paper's sections, particularly the Statement of need, State of the field, and Research impact statement.",
            )

        if word_count > maximum:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"{context}, but at most {maximum} are allowed.",
                "Shorten the paper by moving detailed content, such as API documentation or extended examples, to the software's documentation.",
            )

        return self._CreateResult(module, requirement_data, EvaluateResultValue.Success, f"{context}.")
