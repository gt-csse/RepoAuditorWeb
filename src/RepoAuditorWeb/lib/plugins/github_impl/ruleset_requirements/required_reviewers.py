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
# merging" rule; the required reviewers are a parameter of that rule rather than a rule of its own.
RULE_TYPE = "pull_request"


# The rule names teams rather than people, so it says nothing until a repository has teams whose
# areas differ. A solo maintainer has none, a small team reviews the whole repository together, and
# a large team is where ownership has divided far enough for a named team to mean something.
DEFAULT_VALUES: dict[TeamSize, int] = {
    TeamSize.Solo: 0,
    TeamSize.Small: 0,
    TeamSize.Large: 1,
}


# ----------------------------------------------------------------------
class RequiredReviewersRequirement(Requirement):
    """Validates the number of teams that a ruleset requires to review pull requests changing the file patterns each team is named for."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequiredReviewers",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default is derived from the module's team size, so the parameter is an override
            # that is absent unless the user supplies a count of their own. The count is a minimum
            # because which teams a repository names is its own business; the requirement describes
            # whether the setting is used at all rather than dictating the roster.
            "value": TyperParameter(
                int | None,
                None,
                OptionInfo(
                    help="Minimum number of reviewing teams the ruleset must name, overriding the value implied by the team size; 0 requires that no teams are named.",
                    min=0,
                    max=15,
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

        # The teams are a setting of the pull request rule, so they govern nothing on a branch that
        # does not require one. Reporting a failure here would restate the absence of the pull
        # request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so no reviews are requested.",
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
            The default behavior is to require the number of reviewing teams implied by the size of
            the team maintaining the repository, which is {DEFAULT_VALUES[TeamSize.Solo]} for a
            `{TeamSize.Solo.value}` team, {DEFAULT_VALUES[TeamSize.Small]} for a `{TeamSize.Small.value}`
            team, and at least {DEFAULT_VALUES[TeamSize.Large]} for a `{TeamSize.Large.value}` team.
            This repository is being evaluated as `{team_size.value}`, so the expected value is
            {DEFAULT_VALUES[team_size]}.

            Note that this setting names teams and the files they are responsible for, which is a
            different question from how many approvals a pull request needs in total. That count is
            a separate setting on the same rule, covered by the `RequireApprovals` requirement.

            ## Reasons for this Default

            - The rule routes a review to the people who own the files a change touches rather than
              to whoever is available. An approval count is satisfied by any reviewer with write
              access, so it establishes that somebody looked without establishing that the somebody
              knew what they were looking at.
            - A large team is where that distinction begins to matter. Once a repository holds areas
              that different people are responsible for, a change to one area can collect all of its
              approvals from people who do not work on it, which satisfies the count while leaving
              the change unread by anyone who would recognize a mistake in it.
            - A team is more durable than a person. Naming a team keeps the rule pointing at
              whoever currently holds an area as people join and leave, whereas a rule naming
              individuals would have to be edited each time the roster changed.
            - A solo maintainer is expected to name none because the rule cannot be used at all.
              GitHub does not offer it on user-owned repositories, which contain no teams, so any
              non-zero expectation would be unsatisfiable rather than merely strict.
            - A small team is expected to name none because everyone already reviews everything. A
              team of two to five typically has no division of ownership for the rule to express, so
              naming a team that is a synonym for the whole team adds a rule that changes nothing
              while creating a roster that has to be maintained.
            - Requiring more teams than a repository has owners is worse than requiring none. Each
              named team is another group that must be available before a matching change can land,
              so a count exceeding the areas a project genuinely has turns the rule into a queue.

            ## Reasons to Override this Default

            - The repository contains areas whose changes carry different consequences, such as
              infrastructure, build and release configuration, cryptography, or a published API, and
              each is owned by a team that should see changes to it regardless of who wrote them.
            - The project is a monorepo, where a change touching files its author does not own is
              the normal case rather than the exception, so the count should reflect the number of
              owning teams rather than the size of the maintaining team.
            - Ownership is expressed through a `CODEOWNERS` file instead, in which case the
              `RequireReviewFromCodeOwners` requirement describes the arrangement and this one would
              duplicate it with a second roster that can disagree with the first.
            - A large team is nonetheless organized as a single group with no division of ownership,
              such as one practicing collective ownership or pairing on every change, so a count of
              0 states that arrangement rather than leaving the requirement failing.

            Note that a team is counted here whatever its approval threshold, including zero. A team
            entered with zero approvals is added to the pull request for visibility but does not
            have to approve it, so a roster of such teams satisfies this requirement while gating
            nothing.

            Note also that an approval counts toward the rule only if the team has write permission
            or higher for the repository, so a team named without that permission leaves the pull
            request waiting on a review that cannot be given.

            Note also that actors granted bypass permission on the ruleset may merge without the
            reviews, so the rule describes the path that contributors take rather than one that
            cannot be circumvented.
            """,
        )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})

        # GitHub omits the setting rather than reporting an empty roster when no teams are named, so
        # an absent value and an empty list describe the same ruleset.
        reviewers = cast(list[dict[str, object]], parameters.get("required_reviewers") or [])

        repository_url = cast("GitHubSession", query_data["session"]).github_url
        branch_name = cast(str, query_data["branch"])

        # A requirement of no teams is a statement that the setting must not be used, so a ruleset
        # naming one is reported rather than treated as exceeding a minimum.
        if acceptable_value == 0:
            if not reviewers:
                return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
                4) Clear the **Require review from specific teams** checkbox, removing every team listed beneath it.
                5) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#required-reviewers)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The ruleset requires reviews from {len(reviewers)} team(s), but the requirement specifies that it must not name any.",
                resolution,
                rationale,
                self,
                module,
            )

        if len(reviewers) < acceptable_value:
            # The requirement does not apply unless the pull request rule is enabled, so the setting
            # is already available and the resolution does not need to enable the rule. The teams
            # and patterns are the project's to choose, so the resolution names the count rather
            # than prescribing which teams to enter.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
                4) Check the **Require review from specific teams** checkbox.
                5) Click **Add reviewer** until at least {acceptable_value} team(s) are listed, selecting each one in the **Reviewer** dropdown and entering the **File patterns** it is responsible for.
                6) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#required-reviewers)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The ruleset requires reviews from {len(reviewers)} team(s), but the requirement specifies it must be at least {acceptable_value}.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
