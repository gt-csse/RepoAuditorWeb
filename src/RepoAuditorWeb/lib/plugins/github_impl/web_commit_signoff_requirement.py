import textwrap

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

        rationale = textwrap.dedent(
            """\
            The default behavior is to require contributors to sign off on web-based commits.

            Reasons for this Default
            ------------------------
            - All changes (regardless of where they were made) should go through the same validation process.

            Reasons to Override this Default
            --------------------------------
            - Changes made via the web interface are considered to be benign and should not be subject to
              the standard validation process.
            """,
        )

        if web_commit_signoff_value != acceptable_value:
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's web commit signoff value is '{web_commit_signoff_value}', but the requirement specifies it must be '{acceptable_value}'.",
                "BugBug: This is the resolution!",
                rationale,
                self,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self)
