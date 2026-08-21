from typing import cast, override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement


# ----------------------------------------------------------------------
class WebCommitSignoffRequirement(Requirement):
    """Requirement to validate a repository's web commit signoff status."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "WebCommitSignoff",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "no": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Do not require web commit signoffs."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        web_commit_signoff_value = cast(
            bool, cast(dict, query_data["response"]).get("web_commit_signoff_required", False)
        )
        acceptable_value = not requirement_data["no"]

        if web_commit_signoff_value != acceptable_value:
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's web commit signoff value is '{web_commit_signoff_value}', but the requirement specifies it must be '{acceptable_value}'.",
                None,
                None,
                self,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, None, self)
