import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require deployments to succeed"
# rule.
RULE_TYPE = "required_deployments"


# The rule gates a merge on the environments it names, so a rule that names none is enabled but
# inert; one environment is the fewest that makes the rule do anything.
DEFAULT_VALUE = 1


# ----------------------------------------------------------------------
class RequireSuccessfulDeploymentsRequirement(Requirement):
    """Validates whether a ruleset requires changes to deploy successfully to named environments before branches matching its pattern can be merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireSuccessfulDeployments",
            cast(str, self.__class__.__doc__),
            # The rule presumes the repository defines deployment environments and deploys to them
            # from a pull request, which is a property of the project rather than something that can
            # be inferred from the ruleset, so the user states that it applies by including it.
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # Inclusion already states that the rule is wanted, so the parameter describes how many
            # environments must be named rather than whether the rule is required at all. Zero
            # inverts the expectation for a project that includes the requirement in order to assert
            # that the rule stays off, since a rule that must name no environments is one that must
            # not be present at all.
            "value": TyperParameter(
                int,
                DEFAULT_VALUE,
                OptionInfo(
                    help="Minimum number of deployment environments that must be required; 0 requires that successful deployments are not mandated.",
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

        acceptable_value = cast(int, requirement_data["value"])

        rationale = textwrap.dedent(
            f"""\
            This requirement is not included by default because the rule presumes that the repository
            defines deployment environments and deploys to them from a pull request, which is a
            property of the project rather than something that can be inferred from the ruleset.

            When included, the default behavior is to require that a ruleset mandates successful
            deployments to at least {DEFAULT_VALUE} environment(s).

            ## Reasons for this Default

            - A project that includes this requirement has stated that its changes are expected to
              reach a deployment environment before they merge, so the rule is what makes that
              expectation hold for every pull request rather than only the ones a contributor
              remembers to deploy.
            - A deployment exercises the change in place. Infrastructure, database migrations, and
              configuration are the cases a test suite describes least well, and a deployment that
              fails against them is evidence no status check would have produced.
            - The rule has no effect unless the ruleset names at least one environment, so a minimum
              of {DEFAULT_VALUE} is the fewest that makes the rule do anything. A ruleset that enables
              the checkbox and selects nothing is enabled but inert, which reads as protection that
              is not present.
            - One environment is enough to establish that the change deploys. Requiring more names
              more environments that must each receive a deployment before the merge, which is a
              statement about a project's promotion process rather than about whether the change
              works, so the count is left to the project to raise.

            ## Reasons to Override this Default

            - The project promotes a change through several environments before it merges, such as a
              preview and a staging environment, in which case the count should name each one that a
              merge is expected to wait for.
            - The named environments have diverged from the ones the repository actually deploys to.
              The rule names environments literally, so a renamed or retired environment leaves the
              ruleset naming one that no longer receives deployments, which blocks every pull
              request until the ruleset is edited.
            - Deploying a proposed change is a stronger action than testing it, since the deployment
              targets a real environment with real credentials and real data. A repository that
              accepts pull requests from forks may prefer required status checks, which gate a merge
              on evidence that a change is sound without acting outside the repository.
            - The project deploys only after a merge, so there is nothing to deploy while the pull
              request is open and the rule would block every one of them. Such a project can request
              a count of 0 so that the rule is required to stay off.

            Note that the rule gates the merge rather than the release. A deployment that succeeds
            against the head of a pull request says nothing about the merge result, so it is a weaker
            signal than deploying from the base branch after the merge has landed.
            """,
        )

        # The endpoint reports one rule per ruleset that applies to the branch, so environments
        # named by any matching rule count toward the total.
        deployment_rules = [rule for rule in rules if rule.get("type") == RULE_TYPE]

        environments: list[str] = []

        for rule in deployment_rules:
            parameters = cast(dict[str, object], rule.get("parameters") or {})
            environments += cast(
                list[str],
                parameters.get("required_deployment_environments") or [],
            )

        # A rule that must name no environments is a rule that must not be present, since one that
        # names none is enabled but inert.
        if acceptable_value == 0:
            if not deployment_rules:
                return EvaluateResult(
                    EvaluateResultValue.Success,
                    None,
                    None,
                    rationale,
                    self,
                    module,
                )

            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Clear the **Require deployments to succeed** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset requires successful deployments, but the requirement specifies that it must not.",
                resolution,
                rationale,
                self,
                module,
            )

        # The rule being absent and the rule naming too few environments are fixed by different
        # actions, so they are reported separately rather than as one count that happens to be zero.
        if not deployment_rules:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Check the **Require deployments to succeed** checkbox in the **Branch rules** section.
                4) Select at least {acceptable_value} environment(s) beneath that checkbox.
                5) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset does not require successful deployments.",
                resolution,
                rationale,
                self,
                module,
            )

        if len(environments) < acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            # The rule is already enabled, so the resolution names the environments to add rather
            # than directing the user to the checkbox.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Select at least {acceptable_value} environment(s) beneath the **Require deployments to succeed** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The ruleset requires successful deployments to {len(environments)} environment(s), but the requirement specifies it must be at least {acceptable_value}.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
