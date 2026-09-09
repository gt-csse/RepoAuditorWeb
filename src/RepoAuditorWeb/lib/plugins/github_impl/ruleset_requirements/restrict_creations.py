import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Restrict creations" rule.
RULE_TYPE = "creation"


# ----------------------------------------------------------------------
class RestrictCreationsRequirement(Requirement):
    """Validates whether a ruleset restricts creation of branches matching its pattern, so that only those with bypass permissions can create them."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RestrictCreations",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that creations are restricted."),
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
        restrict_creations_value = any(rule.get("type") == RULE_TYPE for rule in rules)

        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset does not restrict creations, which
            matches GitHub's own default when a branch ruleset is created.

            ## Reasons for this Default

            - The rule governs bringing a name into existence, not what may be pushed to it. A branch
              that already exists is unaffected by it, so on a ruleset targeting an established
              branch the rule protects nothing that the deletion and force-push rules do not already
              protect.
            - A ruleset targeting a pattern rather than a single name commonly covers branches that
              contributors are expected to create, such as `release/*` or `feature/*`. Restricting
              creation there blocks the ordinary act of starting work, and the failure surfaces as a
              rejected push rather than as an explanation of the policy.
            - Creating a branch is reversible and reachable only through the rules that govern
              merging it back. The cost of a wrongly created branch is a stale name; the cost of a
              wrongly blocked creation is contributors unable to begin.
            - Automation that opens pull requests, such as dependency update bots and release
              tooling, creates branches as its first step. Each such actor has to be added to the
              bypass list before the rule takes effect, and one that is missed fails silently until
              someone investigates.

            ## Reasons to Override this Default

            - The ruleset targets a namespace whose names carry meaning that consumers rely on, such
              as `v*` release branches or a `production` deployment branch, where an unsanctioned
              name is itself the problem rather than its contents.
            - The repository is a mirror or a published artifact whose branch set is generated
              rather than authored, where any branch that a person creates is unintended.

            Note that this rule restricts who may create a matching branch rather than preventing
            creation outright. Anyone named in the ruleset's bypass list may still create one, as may
            a repository administrator when the ruleset grants administrators bypass.
            """,
        )

        if restrict_creations_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Restrict creations** checkbox in the **Rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#restrict-creations)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{restrict_creations_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
