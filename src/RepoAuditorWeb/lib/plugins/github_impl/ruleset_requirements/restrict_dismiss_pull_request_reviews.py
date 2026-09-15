import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements import parent_rule
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule; the dismissal restriction is a parameter of that rule rather than a rule of its own.
RULE_TYPE = parent_rule.PULL_REQUEST_RULE_TYPE


# The restriction names the actors that may dismiss in addition to those who always can, so an empty
# roster is the narrowest configuration rather than one that dismisses nobody.
DEFAULT_VALUE = 0


# ----------------------------------------------------------------------
class RestrictDismissPullRequestReviewsRequirement(Requirement):
    """Validates whether a ruleset restricts review dismissal to named actors and how many actors it grants that ability to."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RestrictDismissPullRequestReviews",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the restriction to be enabled, so the parameter names the
            # override rather than the default; a 'require' parameter defaulting to True would be a
            # flag that is already on and cannot be turned off.
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that review dismissal is not restricted to named actors."),
            ),
            # The roster is a separate question from whether the restriction is on, so the count is
            # a maximum rather than a minimum; the requirement is that few actors hold the ability,
            # not that any particular actor does.
            "value": TyperParameter(
                int,
                DEFAULT_VALUE,
                OptionInfo(
                    help="Maximum number of actors the ruleset may allow to dismiss reviews; ignored when '--prohibit' is specified.",
                    min=0,
                    max=100,
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
        *,
        evaluate_all: bool,
    ) -> EvaluateResult:
        pull_request_rule = parent_rule.GetRule(query_data, RULE_TYPE, evaluate_all=evaluate_all)

        # The restriction governs the reviews collected on a pull request, so it has nothing to
        # protect on a branch that does not require one. Reporting a failure here would restate the
        # absence of the pull request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so there are no reviews to dismiss.",
                None,
                None,
                self,
                module,
            )

        acceptable_value = not cast(bool, requirement_data["prohibit"])
        acceptable_actors = cast(int, requirement_data["value"])

        rationale = textwrap.dedent(
            f"""\
            The default behavior is to require that a ruleset restricts review dismissal to named
            actors and that it names at most {DEFAULT_VALUE} of them.

            Note that this differs from GitHub's own default when a branch ruleset is created, where
            the restriction is not selected even once the pull request rule is enabled, leaving
            dismissal available to everyone with write access to the repository.

            ## Reasons for this Default

            - Dismissal is the one action that removes a requirement rather than satisfying it.
              Every other rule on a pull request is met by doing the work, whereas dismissing a
              review discards a reviewer's objection and clears the path to merge without the
              objection ever being addressed.
            - Without the restriction the ability is held by everyone with write access, which is
              the same set of people the approval requirement exists to check. An author who cannot
              approve their own pull request can still dismiss the review that blocks it, so the
              rule that requires another person's agreement is undone by the person it constrains.
            - The blocking review is the one worth protecting. A reviewer who requests changes
              states that the change is not ready, and that state persists until the reviewer
              withdraws it or somebody dismisses it, so unrestricted dismissal makes the strongest
              signal a reviewer can send the easiest one to remove.
            - Naming no actors is the narrowest setting rather than an empty one. Repository
              administrators and those with the maintain role retain the ability regardless of the
              roster, so the rule removes dismissal from everyone else rather than from everyone.
            - Anyone added to the roster is someone who can dismiss a review that is not theirs, so
              each entry widens the exception that the restriction exists to close. Keeping the
              roster empty leaves the ability where the repository's permissions already place it.

            ## Reasons to Override this Default

            - Reviews are dismissed as a matter of routine, such as a project whose reviewers
              frequently leave a blocking review and then become unavailable, where restricting the
              ability moves the delay onto the administrators rather than removing it.
            - A bot or an integration performs dismissal as part of an automated workflow, in which
              case the app must appear on the roster and a maximum of {DEFAULT_VALUE} would report a
              configuration that the project depends on.
            - The repository is maintained by a single person, who holds administrator permission
              and can dismiss regardless, so the restriction describes an arrangement that already
              holds rather than changing anything.
            - A designated group other than the administrators owns review disputes, such as a
              release or security team, and should hold the ability without holding administrator
              permission over the repository.

            Note that the restriction governs who may discard an existing review rather than what
            happens to reviews on their own. Approvals are still dismissed automatically when new
            commits are pushed if the ruleset requests it, which the
            `DismissStalePullRequestApprovals` requirement covers.

            Note also that the restriction does not prevent a reviewer from withdrawing their own
            blocking review, so a change can still proceed once the person who objected is
            satisfied.

            Note also that actors granted bypass permission on the ruleset are not subject to the
            pull request rule at all, so the restriction describes the path that contributors take
            rather than one that cannot be circumvented.
            """,
        )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})

        # GitHub omits the setting rather than reporting a disabled restriction when it is not in
        # use, so an absent value and a disabled one describe the same ruleset.
        dismissal_restriction = cast(dict[str, object], parameters.get("dismissal_restriction") or {})

        restriction_value = bool(dismissal_restriction.get("enabled"))

        # The roster is omitted rather than reported as empty when no actors are named.
        allowed_actors = cast(list[dict[str, object]], dismissal_restriction.get("allowed_actors") or [])

        repository_url = cast("GitHubSession", query_data["session"]).github_url
        branch_name = cast(str, query_data["branch"])

        if restriction_value != acceptable_value:
            action = "Check" if acceptable_value else "Clear"

            # The rule may be absent when every requirement is being evaluated, in which case
            # the steps that reach the setting must enable it first.
            resolution_prefix = parent_rule.GetPullRequestRuleResolutionPrefix(
                query_data,
                evaluate_all=evaluate_all,
            )

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                {resolution_prefix}
                4) {action} the **Restrict who can dismiss pull request reviews** checkbox.
                5) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{restriction_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        # The roster is a setting of the restriction, so it grants nobody anything on a ruleset that
        # was required not to enable the restriction in the first place.
        if acceptable_value and len(allowed_actors) > acceptable_actors:
            # The rule may be absent when every requirement is being evaluated, in which case
            # the steps that reach the setting must enable it first.
            resolution_prefix = parent_rule.GetPullRequestRuleResolutionPrefix(
                query_data,
                evaluate_all=evaluate_all,
            )

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                {resolution_prefix}
                4) Remove actors listed beneath the **Restrict who can dismiss pull request reviews** checkbox until at most {acceptable_actors} remain.
                5) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The ruleset allows {len(allowed_actors)} actor(s) to dismiss reviews, but the requirement specifies it must be at most {acceptable_actors}.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
