import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Restrict deletions" rule.
RULE_TYPE = "deletion"


# ----------------------------------------------------------------------
class RestrictDeletionsRequirement(Requirement):
    """Validates whether a ruleset restricts deletion of the branch, so that only those with bypass permissions can delete it."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RestrictDeletions",
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
                OptionInfo(help="Require that deletions are not restricted."),
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
        restrict_deletions_value = any(rule.get("type") == RULE_TYPE for rule in rules)

        acceptable_value = not cast(bool, requirement_data["prohibit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset restricts deletions, which matches
            GitHub's own default when a branch ruleset is created.

            ## Reasons for this Default

            - Deleting a branch removes the only name that keeps its commits reachable. Nothing
              rejects the deletion and nothing records what the name pointed at, so recovering the
              branch requires someone to still hold the commit hash in a local clone or a reflog
              that has not yet expired.
            - A deletion defeats the protections attached to the branch rather than violating them.
              Required reviews, status checks, and a blocked force push all constrain what may be
              pushed to a branch that exists; none of them apply once the branch is gone.
            - The branch this query targets is the one consumers reference by name. Its deletion
              breaks clones, pull requests opened against it, workflows triggered on it, and
              published links to it, so the cost is borne by everyone reading the repository rather
              than by the person who deleted it.
            - A deletion is a single unconfirmed API call or a click in the branches list, and the
              deleting actor needs only push access. Restricting it converts an irreversible action
              into one that requires bypass permissions.

            ## Reasons to Override this Default

            - The ruleset targets a pattern that intentionally covers transient branches, such as
              release or integration branches that tooling creates and deletes as part of its normal
              operation, where a blocked deletion presents as an unexplained automation failure.
            - The repository is a fork, mirror, or scratch repository whose branches are recreated
              from an upstream source, where the branch carries no history that its upstream does
              not already hold.

            Note that this rule restricts who may delete the branch rather than preventing deletion
            outright. Anyone named in the ruleset's bypass list may still delete it, as may a
            repository administrator when the ruleset grants administrators bypass.
            """,
        )

        if restrict_deletions_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Restrict deletions** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#restrict-deletions)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{restrict_deletions_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
