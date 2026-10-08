from abc import abstractmethod
from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper


# ----------------------------------------------------------------------
class PaperContentRequirement(RationaleRequirement):
    """Requirement that evaluates the contents of the paper, and does not apply when there is no paper."""

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        *,
        evaluate_all: bool,
    ) -> EvaluateResult:
        paper = cast("Paper | None", query_data["paper"])

        if paper is None:
            # The Paper requirement reports the missing file, so it is not reported again here.
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.DoesNotApply,
                "`paper.md` was not found in the repository.",
            )

        return self._EvaluatePaper(module, query_data, requirement_data, paper)

    # ----------------------------------------------------------------------
    @abstractmethod
    def _EvaluatePaper(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        paper: Paper,
    ) -> EvaluateResult:
        """Evaluate the paper."""
