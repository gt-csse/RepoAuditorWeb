import textwrap

from datetime import datetime
from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.minimum_months_requirement import (
    MinimumMonthsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class PublicHistoryRequirement(MinimumMonthsRequirement):
    """Validates that the repository is public and was created at least a minimum number of months ago."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PublicHistory",
            cast(str, self.__class__.__doc__),
            "The repository was created",
            textwrap.dedent(
                """\
                Continue developing the software in the public repository until it has been public for
                the required period, then submit it to JOSS.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that the repository is public and was created at
                least 6 months ago.

                ## Reasons for this Default

                - JOSS requires that the repository has been public for more than six months prior to
                  submission, and its review checklist asks whether the software was developed openly
                  from an early stage.
                - JOSS requires that the software can be cloned and browsed without registration.

                ## Reasons to Override this Default

                - The software is not being prepared for submission to JOSS.

                Note that GitHub does not report when a repository was made public, so the creation date
                is used instead; a repository that was private for part of that period will pass this
                requirement even though JOSS may not consider that period to be public development.
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

        if repository.get("private"):
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                "The repository is private.",
                textwrap.dedent(
                    f"""\
                    1) Open the repository's [settings]({repository["html_url"]}/settings) page.
                    2) In the **Danger Zone** section, click **Change visibility**.
                    3) Select **Change to public** and follow the prompts.

                    See [Setting repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
                    for more information.
                    """,
                ),
            )

        return super()._EvaluateImpl(module, query_data, requirement_data, evaluate_all=evaluate_all)

    # ----------------------------------------------------------------------
    @override
    def _GetDate(self, query_data: dict[str, object]) -> datetime:
        return datetime.fromisoformat(cast(dict, query_data["repository"])["created_at"])
