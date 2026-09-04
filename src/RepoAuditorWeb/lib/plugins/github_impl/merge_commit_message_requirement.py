import textwrap

from enum import StrEnum
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.commit_message_value import (
    CommitMessageSetting,
    EvaluateCommitMessage,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class Values(StrEnum):
    """Enumeration of possible values for the MergeCommitMessageRequirement."""

    DefaultMessage = "default_message"
    PullRequestTitle = "pull_request_title"
    PullRequestTitleAndDescription = "pull_request_title_and_description"


# ----------------------------------------------------------------------
class MergeCommitMessageRequirement(Requirement):
    """Validates the default commit message offered when a pull request is merged with a merge commit."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "MergeCommitMessage",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                Values,
                Values.PullRequestTitle,
                OptionInfo(
                    help="Default commit message for merge commits: 'default_message' uses the classic `Merge pull request #123 from branch` subject with the pull request title as the body; 'pull_request_title' uses the pull request title with an empty body; 'pull_request_title_and_description' uses the pull request title with its description as the body.",
                ),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the merge commit's subject is the pull request
            title and that its body is empty (the **Pull request title** option).

            Note that this differs from the state of a newly created repository, which uses the
            **Default message** option.

            ## Reasons for this Default

            - The classic subject, `Merge pull request #123 from <owner>/<branch>`, describes the
              mechanics of the merge rather than the change it introduced. A log of such subjects
              conveys only that merges happened, so the reader has to open each one to learn what it
              was. The pull request title states the change, which is what a subject line is for.
            - The branch name in the classic subject is transient. It identifies a ref that is
              typically deleted once the pull request merges, so it dates the history with a name that
              no longer resolves while displacing the description of the change.
            - Git convention treats the first line as a short summary, and tooling relies on it:
              `git log --oneline`, `git shortlog`, blame annotations, and most review interfaces show
              the subject alone. A subject that omits the change makes each of these less informative.
            - An empty body keeps the pull request description in one place. The description is
              maintained on the pull request, where it can be corrected after the fact, whereas a copy
              committed into the history cannot be amended once the commit is on the base branch.
            - The pull request number remains in the subject under this option, so the commit still
              links back to its discussion and review.

            ## Reasons to Override this Default

            - The project wants the commit to be self-contained, so that the reasoning survives without
              access to the pull request. This matters when the history may be read outside GitHub, or
              when the repository could move to a host where the pull requests do not follow
              (`pull_request_title_and_description`).
            - Tooling that generates release notes or changelogs from commit bodies has nothing to read
              when the body is empty (`pull_request_title_and_description`).
            - The project relies on the classic subject's branch name, or on tooling that parses the
              `Merge pull request #N` form, and changing it would break that (`default_message`).

            Note that this setting only supplies the message GitHub pre-fills; a user with write
            access can edit it before confirming the merge, so it establishes a default rather than
            enforcing a format. Note also that it applies to merge commits alone, and that the squash
            and rebase methods are configured separately.
            """,
        )

        return EvaluateCommitMessage(
            _SETTING,
            cast(Values, requirement_data["value"]),
            rationale,
            module,
            self,
            query_data,
        )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_SETTING = CommitMessageSetting(
    {
        Values.DefaultMessage: ("MERGE_MESSAGE", "PR_TITLE"),
        Values.PullRequestTitle: ("PR_TITLE", "BLANK"),
        Values.PullRequestTitleAndDescription: ("PR_TITLE", "PR_BODY"),
    },
    {
        Values.DefaultMessage: "Default message",
        Values.PullRequestTitle: "Pull request title",
        Values.PullRequestTitleAndDescription: "Pull request title and description",
    },
    "allow_merge_commit",
    "merge_commit_title",
    "merge_commit_message",
    "merge commit",
    "merge commits",
    "Allow merge commits",
    "Configuring commit merging for pull requests",
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests",
)
