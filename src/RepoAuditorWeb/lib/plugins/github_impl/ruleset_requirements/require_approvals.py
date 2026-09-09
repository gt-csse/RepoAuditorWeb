import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.team_size import TeamSize
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule; the approval count is a parameter of that rule rather than a rule of its own.
RULE_TYPE = "pull_request"


# A solo maintainer has nobody else to ask for an approval, so any non-zero count would block every
# pull request; the count rises with the team because a larger team both has reviewers available and
# benefits more from spreading knowledge of a change.
DEFAULT_VALUES: dict[TeamSize, int] = {
    TeamSize.Solo: 0,
    TeamSize.Small: 1,
    TeamSize.Large: 2,
}


# ----------------------------------------------------------------------
class RequireApprovalsRequirement(Requirement):
    """Validates the number of approving reviews that a ruleset requires before a pull request targeting branches matching its pattern can be merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireApprovals",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default is derived from the module's team size, so the parameter is an override
            # that is absent unless the user supplies a count of their own.
            "value": TyperParameter(
                int | None,
                None,
                OptionInfo(
                    help="Number of approving reviews required, overriding the value implied by the team size.",
                    min=0,
                    max=10,
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
        rules = cast(list[dict[str, object]], query_data["response"])

        # The endpoint reports only the rules that apply, so the absence of the pull request rule
        # means the branch accepts direct pushes.
        pull_request_rule = next((rule for rule in rules if rule.get("type") == RULE_TYPE), None)

        # The count is a setting of the pull request rule, so it governs nothing on a branch that
        # does not require one. Reporting a failure here would restate the absence of the pull
        # request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so no approvals are collected.",
                None,
                None,
                self,
                module,
            )

        team_size = cast(TeamSize, query_data["team_size"])

        acceptable_value = cast(int | None, requirement_data["value"])
        if acceptable_value is None:
            acceptable_value = DEFAULT_VALUES[team_size]

        rationale = textwrap.dedent(
            f"""\
            The default behavior is to require the number of approving reviews implied by the size
            of the team maintaining the repository, which is {DEFAULT_VALUES[TeamSize.Solo]} for a
            `{TeamSize.Solo.value}` team, {DEFAULT_VALUES[TeamSize.Small]} for a `{TeamSize.Small.value}`
            team, and {DEFAULT_VALUES[TeamSize.Large]} for a `{TeamSize.Large.value}` team. This
            repository is being evaluated as `{team_size.value}`, so the expected value is
            {DEFAULT_VALUES[team_size]}.

            Note that a non-zero count differs from GitHub's own default when a branch ruleset is
            created, where the pull request rule may be enabled while requiring no approvals at all.

            ## Reasons for this Default

            - An approval is the only part of a pull request that records a second person's
              judgement. The pull request produces something that can be examined and a status check
              reports what a machine concluded, but neither states that a person read the change, so
              a count of zero permits an author to merge their own work unseen.
            - The count is what gives the surrounding rules force. Requiring a pull request without
              requiring an approval leaves a process whose last step is the author clicking merge,
              which reaches the same result as a direct push by a longer route.
            - GitHub does not allow an author to approve their own pull request, so any count above
              zero guarantees that the reviewer is someone other than the person who wrote the
              change.
            - A second reviewer is where the returns level off. Sauer et al. found that two
              reviewers detect close to the maximum number of defects a review will find and that
              the cost of adding further reviewers is not justified, so a large team is expected to
              require two rather than a number that grows with its headcount.
            - Requiring more approvals than a team can supply is worse than requiring fewer. Each
              approval names a person who must be available before the change can land, so a count
              that exceeds the number of people willing to review turns the rule into a queue and
              pressures the team into granting bypasses that weaken every other rule with it.
            - A solo maintainer is expected to require none because there is nobody else to ask. A
              non-zero count on a single-maintainer repository blocks every pull request
              indefinitely, so the rule would be satisfied only by circumventing it.

            ## Reasons to Override this Default

            - The repository holds code whose failure is expensive or hard to reverse, such as
              infrastructure, cryptography, or a published package, where an additional approval
              buys scrutiny that is worth the delay it introduces.
            - Most changes arrive from contributors outside the maintaining team, in which case the
              approval is the point at which a maintainer takes responsibility for a change they did
              not write, and the count should reflect the maintainers rather than the contributors.
            - The repository is a fork, a mirror, or an archive whose changes are not authored
              locally, so there is no reviewer for whom an approval would mean anything.
            - Review is enforced through a different mechanism, such as a required review from code
              owners or from a named team, which a count alone does not describe.

            Note that the count measures how many approvals are needed rather than how current they
            are. Unless the ruleset also dismisses stale approvals when new commits are pushed or
            requires approval of the most recent push, an approval granted early can carry a change
            that was rewritten afterwards.

            Note also that actors granted bypass permission on the ruleset may merge without the
            approvals, so the count describes the path that contributors take rather than one that
            cannot be circumvented.
            """,
        )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})
        approvals_value = cast(int, parameters.get("required_approving_review_count") or 0)

        if approvals_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            # The requirement does not apply unless the pull request rule is enabled, so the
            # dropdown is already available and the resolution does not need to enable the rule.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Set the **Required approvals** dropdown beneath **Require a pull request before merging** to {acceptable_value}.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{approvals_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
