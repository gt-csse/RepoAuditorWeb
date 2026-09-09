import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule; stale approval dismissal is a parameter of that rule rather than a rule of its own.
RULE_TYPE = "pull_request"


# ----------------------------------------------------------------------
class DismissStalePullRequestApprovalsRequirement(Requirement):
    """Validates whether a ruleset dismisses the approving reviews on a pull request when new commits change the code that those reviews were granted against."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "DismissStalePullRequestApprovals",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the setting to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that stale pull request approvals are not dismissed."),
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
        rules = cast(list[dict[str, object]], query_data["response"])

        # The endpoint reports only the rules that apply, so the absence of the pull request rule
        # means the branch accepts direct pushes.
        pull_request_rule = next((rule for rule in rules if rule.get("type") == RULE_TYPE), None)

        # The setting governs the approvals collected on a pull request, so it has nothing to
        # dismiss on a branch that does not require one. Reporting a failure here would restate the
        # absence of the pull request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so there are no approvals to dismiss.",
                None,
                None,
                self,
                module,
            )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})
        dismiss_value = bool(parameters.get("dismiss_stale_reviews_on_push"))

        acceptable_value = not cast(bool, requirement_data["disallow"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset dismisses stale pull request approvals
            when new commits are pushed.

            Note that this differs from GitHub's own default when a branch ruleset is created, where
            the setting is not selected even once the pull request rule is enabled.

            ## Reasons for this Default

            - An approval is a statement about a diff rather than about a branch. Without this
              setting the approval remains attached to the pull request while the code beneath it is
              replaced, so the merge is authorized by a review of something that is no longer what
              gets merged.
            - The gap it closes is the one a hurried author or a bad actor would use. A pull request
              can be opened small, approved, and then extended with a further commit, and the merge
              button stays enabled throughout, so the approval requirement ends up satisfied by code
              that nobody agreed to.
            - It is what keeps the approval count honest. Requiring approvals establishes how many
              people must agree, and dismissing stale ones establishes that they agreed to the
              current state, so without it the count measures how many people once looked rather
              than how many endorse what will land.
            - Dismissal is driven by the diff changing rather than by any push, so a comment or a
              push that leaves the content identical does not discard the review. Approvals are
              dismissed when a contributor pushes new changes, clicks **Update branch**, or a
              related pull request is merged into the target branch and moves the merge base.
            - The cost falls on the pull requests that changed the most. A change that is approved
              and merged unaltered is never affected, and re-approving a small follow-up commit is
              usually a glance rather than a repeat of the original review.

            ## Reasons to Override this Default

            - The project's pull requests routinely receive many small commits after approval, such
              as review feedback applied one commit at a time, where repeated dismissal turns a
              single review into a sequence of them and trains reviewers to re-approve without
              rereading.
            - The target branch moves quickly enough that merge base changes dismiss approvals on
              pull requests that did not themselves change, in which case reviews are discarded for
              a reason unrelated to the change under review.
            - **Require approval of the most recent reviewable push** is used instead. That setting
              keeps existing approvals and requires only that someone other than the person who made
              the most recent changes approves, which preserves earlier review effort while still
              ensuring another person saw the latest commits.
            - The repository requires no approvals at all, such as one maintained by a single
              person, where there is no approval for the setting to dismiss.

            Note that the setting governs the approvals GitHub has already collected rather than who
            may grant them. It does not prevent the same reviewer from approving again immediately,
            so it ensures that an approval refers to the current diff rather than that the diff
            received a fresh pair of eyes.

            Note also that actors granted bypass permission on the ruleset may merge without
            satisfying the approval requirement at all, so the setting describes the path that
            contributors take rather than one that cannot be circumvented.
            """,
        )

        if dismiss_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            # The requirement does not apply unless the pull request rule is enabled, so the
            # checkbox is already available and the resolution does not need to enable it.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Dismiss stale pull request approvals when new commits are pushed** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{dismiss_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
