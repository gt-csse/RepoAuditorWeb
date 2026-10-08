import textwrap

from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.minimum_months_requirement import (
    MinimumMonthsRequirement,
)

if TYPE_CHECKING:
    from datetime import datetime


# ----------------------------------------------------------------------
class DevelopmentHistoryRequirement(MinimumMonthsRequirement):
    """Validates that the first commit on the branch was authored at least a minimum number of months ago."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "DevelopmentHistory",
            cast(str, self.__class__.__doc__),
            "The first commit was authored",
            textwrap.dedent(
                """\
                Continue developing the software in the repository until its history spans the required
                period, then submit it to JOSS.

                If earlier development took place elsewhere, such as in another repository or version
                control system, import that history (for example, with `git subtree` or `git filter-repo`)
                rather than starting from a single commit.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that the first commit was authored at least 6 months ago.

                ## Reasons for this Default

                - The JOSS review checklist asks whether the project shows sustained development over
                  time, preferably months or years, and JOSS looks for ongoing iteration rather than a
                  single burst of commits.
                - Software that has been refined through use and feedback over time is more likely to be
                  reusable by others than software written in a concentrated window.

                ## Reasons to Override this Default

                - The software is not being prepared for submission to JOSS.

                Note that this requirement only evaluates when development started; reviewers will also
                examine whether development continued throughout that period.
                """,
            ),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetDate(self, query_data: dict[str, object]) -> datetime:
        return cast("datetime", query_data["first_commit_date"])
