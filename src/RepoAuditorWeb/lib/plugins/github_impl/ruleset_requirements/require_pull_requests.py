import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule.
RULE_TYPE = "pull_request"


# ----------------------------------------------------------------------
class RequirePullRequestsRequirement(Requirement):
    """Validates whether a ruleset requires that changes to branches matching its pattern arrive through a pull request rather than a direct push."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequirePullRequests",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the rule to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that pull requests are not mandated."),
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
        pull_requests_value = any(rule.get("type") == RULE_TYPE for rule in rules)

        acceptable_value = not cast(bool, requirement_data["prohibit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset mandates a pull request before
            merging.

            Note that this differs from GitHub's own default when a branch ruleset is created, where
            the rule is not selected.

            ## Reasons for this Default

            - A direct push reaches the branch without producing anything that can be examined
              first. The rule does not add a gate so much as create the object the rest of the
              repository's process attaches to: a review, an approval, a status check, and a
              conversation all refer to a pull request, so a change that never opens one is a change
              those controls cannot describe.
            - The rule is what makes the other rules meaningful. Mandatory status checks and reviews
              constrain how a pull request merges, so a branch that still accepts direct
              pushes leaves a path that bypasses them entirely rather than a path that is merely
              less scrutinized.
            - The record survives the merge. A pull request retains the discussion, the reviewers,
              and the checks that ran against the change, so the reason a commit was accepted
              remains recoverable later, whereas a direct push leaves only the commit message.
            - Enforcing it at the branch is what makes it reliable. A project that expects pull
              requests by convention depends on every contributor remembering under time pressure,
              and the pushes that skip the process are the ones made in a hurry rather than the ones
              that were least important.
            - The cost is small for work that was going to be reviewed anyway. The rule asks only
              that a pull request be opened, and a ruleset that sets no required approvals permits
              the author to merge their own pull request immediately.

            ## Reasons to Override this Default

            - Automation pushes to the branch directly, such as a release workflow that commits a
              version bump or a job that regenerates checked-in artifacts, in which case a bypass
              entry for that actor is usually preferable to disabling the rule for everyone.
            - The repository is maintained by a single person for whom a pull request per change is
              a step with no reviewer at the end of it, such as a personal project or a scratch
              repository.
            - The branch receives a history produced elsewhere, such as a mirror or an import, whose
              commits cannot be routed through a pull request.

            Note that the rule constrains how a change reaches the branch rather than who may
            approve it. Whether a pull request needs an approving review, a code owner's approval,
            or resolved conversations is governed by that rule's own settings, so a ruleset that
            requires a pull request and nothing else still permits a change to merge unreviewed.

            Note also that actors granted bypass permission on the ruleset may push to the branch
            directly, so the rule describes the path that contributors take rather than one that
            cannot be circumvented.
            """,
        )

        if pull_requests_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require a pull request before merging** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{pull_requests_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
