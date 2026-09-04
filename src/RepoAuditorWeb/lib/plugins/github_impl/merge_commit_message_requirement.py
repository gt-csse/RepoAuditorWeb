import textwrap

from enum import StrEnum
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.restricted_value import GetRestrictedValue
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class Values(StrEnum):
    """Enumeration of possible values for the MergeCommitMessageRequirement."""

    DefaultMessage = "default_message"
    PullRequestTitle = "pull_request_title"
    PullRequestTitleAndDescription = "pull_request_title_and_description"


# ----------------------------------------------------------------------
def _GetUILabel(title: object, message: object) -> str:
    """Return the quoted dropdown label for a pairing of the two API fields."""

    # A pairing that the dropdown cannot produce has no label to report, so the API values are
    # named directly rather than being forced onto the nearest option. The quoting is applied here
    # so that this case is not wrapped in quotes that suggest it is a label.
    label = _UI_LABELS_BY_API_VALUES.get(cast(tuple[str, str], (title, message)))

    return f"'{label}'" if label is not None else f"title '{title}' with message '{message}'"


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
        value = cast(Values, requirement_data["value"])

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

        expected_title, expected_message = _API_VALUES[value]

        # The dropdown configures the message GitHub pre-fills when a pull request is merged with a
        # merge commit, so it has nothing to govern in a repository that disallows the method. The
        # setting is retained by GitHub while the checkbox is unchecked, which means an unrelated
        # value here is inert rather than a misconfiguration.
        allow_merge_commit_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "allow_merge_commit",
            "merge commit message settings",
        )

        if isinstance(allow_merge_commit_value, EvaluateResult):
            return allow_merge_commit_value

        if not allow_merge_commit_value:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The repository does not allow merge commits, so no default merge commit message is offered.",
                None,
                rationale,
                self,
                module,
            )

        # The two fields are reported together, so a single visibility check covers both.
        merge_commit_title_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "merge_commit_title",
            "merge commit message settings",
        )

        if isinstance(merge_commit_title_value, EvaluateResult):
            return merge_commit_title_value

        merge_commit_message_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "merge_commit_message",
            "merge commit message settings",
        )

        if isinstance(merge_commit_message_value, EvaluateResult):
            return merge_commit_message_value

        if merge_commit_title_value != expected_title or merge_commit_message_value != expected_message:
            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) Ensure that the **Allow merge commits** checkbox is checked.
                4) Select **{_UI_LABELS[value]}** in the dropdown beneath it.

                See [Configuring commit merging for pull requests](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests)
                for more information.
                """,
            )

            # The dropdown label is reported rather than the API values, because the label is what
            # the user sees in the settings page and what the resolution asks them to select.
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's default merge commit message is {_GetUILabel(merge_commit_title_value, merge_commit_message_value)}, but the requirement specifies it must be '{_UI_LABELS[value]}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# GitHub presents this setting as a single dropdown, but the API models it as a pair of fields whose
# values do not resemble the dropdown labels. Only these three pairings are reachable through the
# UI, so a repository reporting any other pairing was configured through the API.
_API_VALUES: dict[Values, tuple[str, str]] = {
    Values.DefaultMessage: ("MERGE_MESSAGE", "PR_TITLE"),
    Values.PullRequestTitle: ("PR_TITLE", "BLANK"),
    Values.PullRequestTitleAndDescription: ("PR_TITLE", "PR_BODY"),
}


# ----------------------------------------------------------------------
# The dropdown label GitHub shows for each value, used to describe what the user must select.
_UI_LABELS: dict[Values, str] = {
    Values.DefaultMessage: "Default message",
    Values.PullRequestTitle: "Pull request title",
    Values.PullRequestTitleAndDescription: "Pull request title and description",
}


# ----------------------------------------------------------------------
_UI_LABELS_BY_API_VALUES: dict[tuple[str, str], str] = {
    api_values: _UI_LABELS[value] for value, api_values in _API_VALUES.items()
}
