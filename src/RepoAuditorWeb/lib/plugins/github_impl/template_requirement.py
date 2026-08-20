from typing import cast, override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement


# ----------------------------------------------------------------------
class TemplateRequirement(Requirement):
    """Requirement to validate a repository's template status."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Template",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository is a template repository."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        is_template_value = cast(dict, query_data["response"]).get("is_template", False)
        acceptable_value = cast(bool, requirement_data["require"])

        if is_template_value != acceptable_value:
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's template status is '{is_template_value}', but the requirement specifies it must be '{acceptable_value}'.",
                None,
                None,
                self,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, None, self)
