import textwrap

from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class IssuesRequirement(RationaleRequirement):
    """Validates that issues are enabled, so that reviewers and users can report problems."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Issues",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require that issues are enabled.

                ## Reasons for this Default

                - JOSS requires that the repository permits individuals to create issues against it.
                - JOSS reviewers report problems found during the review as issues in the software's
                  repository, and authors respond to them there.

                ## Reasons to Override this Default

                - The project tracks issues in another system that anyone can access without
                  registration, and the README links to it.
                """,
            ),
        )

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
        repository = cast(dict, query_data["repository"])

        if repository.get("has_issues"):
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Success,
                "Issues are enabled.",
            )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Error,
            "Issues are disabled.",
            textwrap.dedent(
                f"""\
                1) Open the repository's [settings]({repository["html_url"]}/settings) page.
                2) In the **Features** section, check **Issues**.

                See [Disabling issues](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-issues)
                for more information.
                """,
            ),
        )
