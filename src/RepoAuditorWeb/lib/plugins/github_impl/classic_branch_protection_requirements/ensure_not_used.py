import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class EnsureNotUsedRequirement(Requirement):
    """Validates whether the branch is protected by a ruleset rather than a classic branch protection rule, which GitHub no longer builds upon."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "EnsureBranchProtectionsAreNotUsed",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The query only produces data when a classic rule is in use, so the default outcome is
            # an error; the parameter names the override rather than the default.
            "permit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Allow the branch to be protected by a classic branch protection rule."),
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
        # This query collects data only when a classic branch protection rule governs the branch,
        # so reaching this point is itself the observation being evaluated.
        classic_branch_protection_value = True
        acceptable_value = cast(bool, requirement_data["permit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the branch is governed by a ruleset rather than
            a classic branch protection rule. Both mechanisms protect a branch and GitHub enforces
            both, but rulesets are the framework GitHub continues to build upon.

            ## Reasons for this Default

            - Only a single branch protection rule applies to a branch at a time, so when several
              rules match it, the configuration that is enforced is not the union of them and is not
              evident from reading them. Rulesets layer instead, and every applicable ruleset is
              enforced.
            - A classic rule is visible only to those who can administer the repository, so
              contributors cannot confirm what governs the branch they are pushing to. Anyone with
              read access can view a repository's active rulesets.
            - A ruleset carries an enforcement status, so it can be disabled and re-enabled without
              being deleted and recreated. Suspending a classic rule means deleting it, which
              discards its configuration.
            - Rules that exist only for rulesets are unavailable while a classic rule governs the
              branch, including restrictions on commit metadata such as commit messages and author
              email addresses, and rules that target tags and pushes rather than branches.
            - Bypass is coarse for a classic rule: it applies to administrators and to roles holding
              the bypass permission unless bypassing is disallowed for everyone. A ruleset names the
              specific actors, teams, and apps that may bypass it.

            ## Reasons to Override this Default

            - A migration to rulesets is in progress and the classic rule is deliberately retained
              until the replacement ruleset has been verified, given that both are enforced
              together and the most restrictive form of a conflicting rule applies.
            - The repository is on a GitHub Enterprise Server release predating repository rulesets,
              where a classic rule is the only protection mechanism available.
            - Tooling outside the repository manages the classic rule through the branch protection
              APIs and has no ruleset equivalent, so removing the rule would cause that tooling to
              recreate or fail against it.

            Note that this requirement concerns which mechanism protects the branch, not how
            strictly it is protected. A classic rule may well be configured more strictly than the
            ruleset that would replace it.
            """,
        )

        if classic_branch_protection_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Branches settings]({repository_url}/settings/branches) page.
                2) Click the **Convert to ruleset** button on the classic branch protection rule whose branch name pattern matches `{branch_name}`.
                3) Enter a name for each ruleset that will be created.
                4) Review the **New behavior** section to confirm that the rules carry over as expected.
                5) Check the **Delete branch protection rule once migration is done** checkbox.
                6) Click the **Create ruleset** button.

                Note that **Require conversation resolution before merging** is not carried over,
                because rulesets express it within the pull request rule; enable it there afterwards
                if the classic rule required it.

                See [Converting branch protections to rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/converting-branch-protections-to-rulesets)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{classic_branch_protection_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
