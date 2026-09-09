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
# merging" rule; code owner review is a parameter of that rule rather than a rule of its own.
RULE_TYPE = "pull_request"


# The rule names a specific person for each path, so it presumes there is somebody other than the
# author to name, which a team cannot be assumed to have.
DEFAULT_VALUE = False


# A large team is where knowing who to ask stops being obvious, so it is the one size for which
# naming an owner is expected rather than presumed unavailable.
TEAM_SIZE_OVERRIDES: dict[TeamSize, bool] = {
    TeamSize.Large: True,
}


# ----------------------------------------------------------------------
class RequireReviewFromCodeOwnersRequirement(Requirement):
    """Validates whether a ruleset requires approval from the owners named in CODEOWNERS when a pull request modifies the paths that they own."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireReviewFromCodeOwners",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The value is implied by the module's team size, so the parameter is an override that
            # is absent unless the user states an expectation of their own.
            "require": TyperParameter(
                bool | None,
                None,
                OptionInfo(
                    help="Require review from code owners, overriding the value implied by the team size.",
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

        # The setting governs who must approve a pull request, so it governs nothing on a branch
        # that does not require one. Reporting a failure here would restate the absence of the pull
        # request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so no code owner review is requested.",
                None,
                None,
                self,
                module,
            )

        team_size = cast(TeamSize, query_data["team_size"])

        # An absent value leaves the team size to decide, while an explicit one overrides it in
        # either direction.
        require = cast(bool | None, requirement_data["require"])

        acceptable_value = TEAM_SIZE_OVERRIDES.get(team_size, DEFAULT_VALUE) if require is None else require

        rationale = textwrap.dedent(
            f"""\
            The default behavior is to require that a ruleset does not request review from code
            owners, which matches GitHub's own default when a branch ruleset is created. The size of
            the team maintaining the repository overrides that default for a
            `{TeamSize.Large.value}` team, where the expected value is
            `{TEAM_SIZE_OVERRIDES[TeamSize.Large]}` instead. This repository is being evaluated as
            `{team_size.value}`, so the expected value is
            `{TEAM_SIZE_OVERRIDES.get(team_size, DEFAULT_VALUE)}`.

            ## Reasons for this Default

            - The rule presumes there is somebody other than the author to name for a path, which a
              team cannot be assumed to have. GitHub does not accept the approval of a pull request
              author toward this requirement, so a sole owner who changes their own paths cannot
              satisfy the rule and the pull request is blocked until somebody bypasses it.
            - The rule only acts where an owner is named. A repository with no CODEOWNERS file, or
              one whose entries do not cover the paths that change most, gains the appearance of
              ownership review on changes that receive none.
            - Concentrated ownership becomes a queue. When owners are named for paths that change
              constantly, every pull request waits on the same small group, which pressures the team
              into granting bypasses that weaken every other rule with it.
            - A small team that already reviews every change and knows the whole codebase gains a
              routing step that resolves to the same reviewers it would have reached anyway.

            ## Reasons for the `{TeamSize.Large.value}` Team Override

            - A count of approvals states how many people must agree, but not which people. On a
              large codebase the reviewer who happens to be available is often not the one who knows
              the code being changed, so an approval count alone can be satisfied entirely by people
              with no familiarity with what was modified.
            - The rule routes each change to the people who own the paths it touches. GitHub
              requests those owners automatically when a pull request modifies their paths, so the
              expertise is applied without the author having to know who to ask.
            - Ownership is what makes review durable as the team grows. A large team turns over and
              specializes, and CODEOWNERS records which parts of the tree each group is responsible
              for in a file that is itself reviewed, rather than in convention that new contributors
              must absorb.
            - It protects the sensitive paths specifically. Entries covering release configuration,
              CI workflows, or the CODEOWNERS file itself ensure that a change to how the repository
              builds and deploys is seen by the people accountable for it, which a general approval
              count treats no differently from a change to a comment.

            ## Reasons to Override this Default

            - A CODEOWNERS file names owners with the availability to review, whatever the size of
              the team. The rule is what makes GitHub request them automatically, so a team that
              maintains the file deliberately gets no benefit from leaving the rule off.
            - Specific paths carry consequences out of proportion to their size, such as release
              configuration, CI workflows, or the CODEOWNERS file itself, and the people accountable
              for them are not whoever is available to approve.
            - A `{TeamSize.Large.value}` repository is a fork, a mirror, or an archive whose changes
              are not authored locally, so there are no owners for whom an approval would mean
              anything.
            - A `{TeamSize.Large.value}` repository has no CODEOWNERS file, or one whose entries do
              not cover the paths that change most, so the override expects a rule that would
              require nothing.

            Note that the rule depends on the CODEOWNERS file rather than on the ruleset. Entries
            must name people or teams with write access, invalid lines are skipped rather than
            reported as a failure, and the last matching pattern for a path wins, so a rule that is
            enabled can still require nothing if the file names nobody for the paths that changed.

            Note also that an approval from any one of the owners named for a path satisfies the
            rule, and that actors granted bypass permission on the ruleset may merge without it, so
            the setting describes the path that contributors take rather than one that cannot be
            circumvented.
            """,
        )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})
        code_owners_value = bool(parameters.get("require_code_owner_review"))

        if code_owners_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            # The requirement does not apply unless the pull request rule is enabled, so the
            # checkbox is already available and the resolution does not need to enable it.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require review from Code Owners** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{code_owners_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
