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
    """Enumeration of possible values for the SquashCommitMessageRequirement."""

    DefaultMessage = "default_message"
    PullRequestTitle = "pull_request_title"
    PullRequestTitleAndCommitDetails = "pull_request_title_and_commit_details"
    PullRequestTitleAndDescription = "pull_request_title_and_description"


# ----------------------------------------------------------------------
class SquashCommitMessageRequirement(Requirement):
    """Validates the default commit message offered when a pull request is merged by squashing."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SquashCommitMessage",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                Values,
                Values.PullRequestTitleAndCommitDetails,
                OptionInfo(
                    help="Default commit message for squash commits: 'default_message' uses the single commit's subject and body, or the pull request title with a list of commits when the branch has more than one; 'pull_request_title' uses the pull request title with an empty body; 'pull_request_title_and_commit_details' uses the pull request title with the squashed commits' messages as the body; 'pull_request_title_and_description' uses the pull request title with the pull request description as the body.",
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
            The default behavior is to require that the squash commit's subject is the pull request
            title and that its body contains the messages of the commits being squashed (the **Pull
            request title and commit details** option).

            Note that this differs from the state of a newly created repository, which uses the
            **Default message** option.

            ## Reasons for this Default

            - Squashing discards the commits it replaces, so any information recorded only in their
              messages is lost when the branch is deleted. This option is the only one that carries
              those messages onto the base branch, which keeps the reasoning behind each step of the
              change reachable from the history rather than from a branch that no longer exists.
            - A pull request approved as a series of commits is reviewed as that series. Retaining the
              messages preserves the account of the work that the reviewer read, so the commit that
              lands describes the same change the review covered.
            - The pull request title is a stable subject. The **Default message** option takes the
              subject from the single commit when a branch has one commit and from the pull request
              title when it has more, so the subject of a squash commit depends on how the branch
              happened to be structured. Fixing it to the title makes `git log --oneline` and
              `git shortlog` consistent across merges.
            - The pull request number is appended to the subject under this option, so the commit
              still links back to its discussion and review.
            - The commit body is the copy that survives without GitHub. Repository archives, mirrors,
              and clones carry commit messages, while pull request bodies and their commit lists are
              host metadata that a `git clone` does not include.

            ## Reasons to Override this Default

            - The branch's commits are fixups, merges of the base branch, or work-in-progress markers
              that carry no meaning after review, in which case copying them into the body adds noise
              rather than information (`pull_request_title` or
              `pull_request_title_and_description`).
            - The project maintains the account of the change in the pull request description instead
              of in the commits, and wants that description to be what lands
              (`pull_request_title_and_description`).
            - Tooling generates release notes from commit bodies and expects a curated body rather
              than a concatenation of the branch's messages (`pull_request_title_and_description`).
            - The project relies on a single-commit branch's own subject and body reaching the base
              branch unaltered (`default_message`).

            Note that this setting only supplies the message GitHub pre-fills; a user with write
            access can edit it before confirming the merge, so it establishes a default rather than
            enforcing a format. Note also that it applies to squash commits alone, and that the merge
            commit method is configured separately. A squash commit carries no information about the
            authorship or signatures of the commits it replaces regardless of this setting, which is
            a property of the method rather than of the message.
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
        Values.DefaultMessage: ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"),
        Values.PullRequestTitle: ("PR_TITLE", "BLANK"),
        Values.PullRequestTitleAndCommitDetails: ("PR_TITLE", "COMMIT_MESSAGES"),
        Values.PullRequestTitleAndDescription: ("PR_TITLE", "PR_BODY"),
    },
    {
        Values.DefaultMessage: "Default message",
        Values.PullRequestTitle: "Pull request title",
        Values.PullRequestTitleAndCommitDetails: "Pull request title and commit details",
        Values.PullRequestTitleAndDescription: "Pull request title and description",
    },
    "allow_squash_merge",
    "squash_merge_commit_title",
    "squash_merge_commit_message",
    "squash commit",
    "squash merging",
    "Allow squash merging",
    "Configuring commit squashing for pull requests",
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests",
)
