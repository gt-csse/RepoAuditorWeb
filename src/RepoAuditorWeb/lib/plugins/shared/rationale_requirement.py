from typing import override, TYPE_CHECKING

from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Markdown, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class RationaleRequirement(Requirement):
    """Requirement that returns its rationale only when its default values are in use."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,
        rationale: Markdown,
        *,
        requires_explicit_include: bool = False,
    ) -> None:
        super().__init__(name, description, requires_explicit_include=requires_explicit_include)

        self._rationale = rationale

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {}

    # ----------------------------------------------------------------------
    def _CreateResult(
        self,
        module: Module,
        requirement_data: dict[str, object],
        result: EvaluateResultValue,
        context: Markdown,
        resolution: Markdown | None = None,
    ) -> EvaluateResult:
        return EvaluateResult(
            result,
            context,
            resolution,
            self._rationale if self.UsesDefaultValues(requirement_data) else None,
            self,
            module,
        )
