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


# ----------------------------------------------------------------------
class RequireSuccessfulDeploymentsRequirement(Requirement):
    """Validates whether a ruleset requires changes to deploy successfully to named environments before branches matching its pattern can be merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireSuccessfulDeployments",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that deployments to succeed are required."),
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

        environments: list[str] = []
        required_deployments_value = False

        for rule in rules:
            if rule.get("type") != RULE_TYPE:
                continue

            required_deployments_value = True

            parameters = cast(dict[str, object], rule.get("parameters") or {})
            environments += cast(
                list[str],
                parameters.get("required_deployment_environments") or [],
            )

        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to expect that a ruleset does not require successful
            deployments, which matches GitHub's own default when a branch ruleset is created.

            ## Reasons for this Default

            - The rule is expressed in terms of deployment environments, so it presumes the
              repository defines environments and runs a workflow that deploys to them. A
              repository that publishes no deployments cannot satisfy the rule, and one that
              deploys only after a merge has nothing to deploy while the pull request is open.
            - The rule names environments literally. Renaming or retiring an environment leaves the
              ruleset naming one that no longer receives deployments, which blocks every pull
              request until the ruleset is edited, and the failure surfaces as an unmergeable pull
              request rather than as an error where the rename occurred.
            - Deploying a proposed change is a stronger action than testing it. The deployment
              targets a real environment with real credentials and real data, so the rule grants
              every pull request, including one from a fork, the ability to reach that environment
              before the change has been reviewed.
            - Required status checks already gate a merge on evidence that a change is sound, and
              they neither require an environment nor act outside the repository. A project that
              wants a build, a test suite, or a preview to pass can require it without also
              requiring that a deployment be recorded.
            - The rule gates the merge rather than the release. A deployment that succeeds against
              the head of a pull request says nothing about the merge result, so the rule is a
              weaker signal than deploying from the base branch after the merge has landed.

            ## Reasons to Override this Default

            - The project maintains a staging or preview environment that every change is expected
              to reach before it merges, so the deployment is a step contributors already perform
              and the rule enforces what is otherwise a convention.
            - The change under review is difficult to validate without exercising it in place, such
              as one that alters infrastructure, database migrations, or configuration whose
              behavior does not appear in a test suite.
            - The project deploys from pull requests already and treats a failed deployment as
              disqualifying, in which case the rule records a decision the project makes by hand.

            Note that the rule has no effect unless the ruleset names at least one environment, so a
            ruleset that enables it without selecting environments does not satisfy the requirement.
            """,
        )

        if required_deployments_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require deployments to succeed** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{required_deployments_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        # The rule gates a merge on the environments it names, so one that names none is enabled but
        # inert; it is reported separately because the rule is present as requested.
        if required_deployments_value and not environments:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Select at least one environment under the **Require deployments to succeed** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset requires successful deployments, but does not name any environments to deploy to.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
