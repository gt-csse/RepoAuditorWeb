import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require code scanning results"
# rule.
RULE_TYPE = "code_scanning"


# The rule gates a merge on the tools it names, so a rule that names none is enabled but inert; one
# tool is the fewest that makes the rule do anything.
DEFAULT_VALUE = 1


# ----------------------------------------------------------------------
class RequireCodeScanningResultsRequirement(Requirement):
    """Validates whether a ruleset requires named code scanning tools to report results below their alert thresholds before branches matching its pattern can be merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireCodeScanningResults",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The parameter describes how many tools must be named rather than whether the rule is
            # required at all. Zero inverts the expectation, since a rule that must name no tools is
            # one that must not be present at all.
            "value": TyperParameter(
                int,
                DEFAULT_VALUE,
                OptionInfo(
                    help="Minimum number of code scanning tools that must be required; 0 requires that code scanning results are not mandated.",
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
            The default behavior is to require that a ruleset mandates results from at least
            {DEFAULT_VALUE} code scanning tool(s) before merging.

            Note that this differs from GitHub's own default when a branch ruleset is created,
            where the rule is not selected.

            ## Reasons for this Default

            - Code scanning looks for a class of defect that neither review nor a test suite
              reliably finds. Injection, unsafe deserialization, and path traversal are properties
              of how data flows through the code rather than of whether it produces the right
              answer, so a passing test and an approving reviewer can both be satisfied by a change
              that introduces one.
            - Scanning without gating produces a backlog rather than a control. A workflow that
              analyzes every pull request files its alerts and the merge proceeds regardless, so
              the finding arrives on the default branch alongside the code that caused it unless
              the ruleset requires the tool to report clean.
            - The cost of a vulnerability rises after the merge. An alert raised while the pull
              request is open is fixed by the author who still has the change in mind, whereas one
              raised afterward is triaged, scheduled, and fixed by whoever is available, often
              against code they did not write.
            - The rule also blocks a merge when the tool has not run or is still analyzing, which
              is what keeps it from being satisfied by a pull request that produced no results at
              all.
            - The rule has no effect unless the ruleset names at least one tool, so a minimum of
              {DEFAULT_VALUE} is the fewest that makes the rule do anything. A ruleset that enables
              the rule and names nothing is enabled but inert, which reads as protection that is
              not present.
            - One tool is enough to establish that the change was scanned. Which analyzers a
              project runs is a property of the languages it uses and the licenses it holds rather
              than of its ruleset, so the count is left to the project to raise.

            ## Reasons to Override this Default

            - The project runs several analyzers whose findings do not overlap, such as CodeQL
              alongside a third-party scanner uploading SARIF, in which case the count should name
              each one that a merge is expected to wait for.
            - Code scanning is not available to the repository. The rule depends on code scanning
              being enabled, which requires GitHub Advanced Security for a private repository, so
              a project without it has no tool to name and the rule would block every pull request.
              Such a project can request a count of 0 so that the rule is required to stay off.
            - The repository holds content that no analyzer supports, such as documentation,
              assets, or configuration, where there are no results to require.
            - The named tool has diverged from the one the repository runs. The rule names a tool
              by the name it uploads results under, so a change of analyzer leaves the ruleset
              waiting on results that will never arrive, which blocks every pull request until the
              ruleset is edited.

            Note that the rule gates the merge on the thresholds configured for each tool rather
            than on the presence of alerts. A tool whose **Alerts** and **Security alerts**
            thresholds are both set to **None** is named by the rule and blocks nothing, so the
            count describes how many tools are named rather than how strictly each is enforced.

            Note also that actors granted bypass permission on the ruleset may merge with alerts
            outstanding, so the rule describes the path that contributors take rather than one that
            cannot be circumvented.
            """,
        )

        # The endpoint reports one rule per ruleset that applies to the branch, so tools named by
        # any matching rule count toward the total.
        code_scanning_rules = [rule for rule in rules if rule.get("type") == RULE_TYPE]

        tools: list[dict[str, object]] = []

        for rule in code_scanning_rules:
            parameters = cast(dict[str, object], rule.get("parameters") or {})
            tools += cast(
                list[dict[str, object]],
                parameters.get("code_scanning_tools") or [],
            )

        # A rule that must name no tools is a rule that must not be present, since one that names
        # none is enabled but inert.
        if acceptable_value == 0:
            if not code_scanning_rules:
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
                3) Clear the **Require code scanning results** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-code-scanning-results)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset requires code scanning results, but the requirement specifies that it must not.",
                resolution,
                rationale,
                self,
                module,
            )

        # The rule being absent and the rule naming too few tools are fixed by different actions,
        # so they are reported separately rather than as one count that happens to be zero.
        if not code_scanning_rules:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Check the **Require code scanning results** checkbox in the **Branch rules** section.
                4) Add at least {acceptable_value} code scanning tool(s) beneath that checkbox.
                5) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-code-scanning-results)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset does not require code scanning results.",
                resolution,
                rationale,
                self,
                module,
            )

        if len(tools) < acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            # The rule is already enabled, so the resolution names the tools to add rather than
            # directing the user to the checkbox.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Add at least {acceptable_value} code scanning tool(s) beneath the **Require code scanning results** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-code-scanning-results)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The ruleset requires {len(tools)} code scanning tool(s), but the requirement specifies it must be at least {acceptable_value}.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
