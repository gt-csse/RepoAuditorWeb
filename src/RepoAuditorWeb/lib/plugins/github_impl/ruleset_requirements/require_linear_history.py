import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require linear history" rule.
RULE_TYPE = "required_linear_history"


# ----------------------------------------------------------------------
class RequireLinearHistoryRequirement(Requirement):
    """Validates whether a ruleset requires a linear history for branches matching its pattern, which prevents merge commits and forces squash or rebase merges."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireLinearHistory",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that a linear history is required."),
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
        linear_history_value = any(rule.get("type") == RULE_TYPE for rule in rules)

        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to expect that a ruleset does not require a linear history,
            which matches GitHub's own default when a branch ruleset is created.

            ## Reasons for this Default

            - The rule forbids merge commits, so it leaves squash merging and rebase merging as the
              only ways a pull request can land. Both rewrite the branch's commits into new objects,
              and the signatures those commits carried do not follow them, so the rule buys a linear
              history at the cost of every contributor signature on the base branch.
            - These requirements default to allowing merge commits and disallowing both squash
              merging and rebase merging, which makes the merge commit the only method a pull request
              may use. Requiring a linear history alongside that configuration leaves a pull request
              with no permitted merge method at all.
            - The rule discards the record of the integration. A merge commit names both the base
              branch and the merged branch as parents, which is what allows `git log --first-parent`
              to read as a list of integrations; a linear history has no such record and cannot
              distinguish a merged branch from a sequence of direct commits.
            - Unlike the branch protection rule of the same name, the ruleset evaluates the history
              that is already present rather than only the commits being pushed. Enabling it on a
              repository whose branch already contains merge commits rejects every subsequent push,
              which cannot be resolved without rewriting the history.
            - Linearity is a property of how the history reads rather than of what it admits. The
              rules that determine whether a change is fit to land, such as requiring a pull request,
              requiring status checks, and requiring signatures, are unaffected by whether the
              commits sit in a line.

            ## Reasons to Override this Default

            - The project treats a pull request as one logical change and has standardized on squash
              merging, in which case the history is already linear and the rule enforces on the
              branch what the repository's merge settings express as a preference.
            - The project relies on tooling that assumes a total order of commits, such as bisecting
              scripts, release automation that derives a changelog by walking commits, or a
              deployment process that identifies a revision by its position in the history.
            - The repository is new or its history was rewritten deliberately, so no merge commit is
              present to trip the evaluation of the existing history.

            Note that the rule cannot be satisfied unless the repository allows squash merging or
            rebase merging, so enabling it while merge commits are the only permitted method
            presents contributors with a merge button that the rule refuses.
            """,
        )

        if linear_history_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require linear history** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-linear-history)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{linear_history_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
