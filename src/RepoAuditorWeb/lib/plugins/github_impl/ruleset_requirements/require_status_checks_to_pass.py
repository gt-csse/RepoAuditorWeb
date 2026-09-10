import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require status checks to pass"
# rule.
RULE_TYPE = "required_status_checks"


# The rule gates a merge on the checks it names, so a rule that names none is enabled but inert;
# one check is the fewest that makes the rule do anything.
DEFAULT_VALUE = 1


# ----------------------------------------------------------------------
class RequireStatusChecksToPassRequirement(Requirement):
    """Validates whether a ruleset requires named status checks to pass before changes to branches matching its pattern can be merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireStatusChecksToPass",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The parameter describes how many checks must be named rather than whether the rule is
            # required at all. Zero inverts the expectation, since a rule that must name no checks
            # is one that must not be present at all.
            "value": TyperParameter(
                int,
                DEFAULT_VALUE,
                OptionInfo(
                    help="Minimum number of status checks that must be required; 0 requires that status checks are not mandated.",
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
            The default behavior is to require that a ruleset mandates at least {DEFAULT_VALUE}
            status check(s) pass before merging.

            Note that this differs from GitHub's own default when a branch ruleset is created,
            where the rule is not selected.

            ## Reasons for this Default

            - A status check is the only control that examines the change itself. A pull request
              produces something to look at and an approval records that a person looked, but
              neither establishes that the code builds or that its tests pass, so a ruleset without
              this rule can merge a branch that was never known to work.
            - Running the checks is not the same as requiring them. A workflow that runs on every
              pull request reports its result beside the merge button, but nothing stops the merge
              while it is failing or still in progress, so the evidence is produced and then
              ignored unless the ruleset names the check.
            - It catches what review does not. A reviewer reads for intent and design, while a
              check reports on compilation, tests, and lint uniformly and without fatigue, so the
              two find different classes of defect and neither substitutes for the other.
            - The check is what keeps the branch releasable. Enforcing it at merge time is what
              makes a green default branch a property of the repository rather than a state that
              happens to hold between a breakage and its discovery.
            - The rule has no effect unless the ruleset names at least one check, so a minimum of
              {DEFAULT_VALUE} is the fewest that makes the rule do anything. A ruleset that enables
              the rule and names nothing is enabled but inert, which reads as protection that is
              not present.
            - One check is enough to establish that the change was verified. Which checks a project
              runs and how it divides them across jobs is a property of its build rather than of
              its ruleset, so the count is left to the project to raise.

            ## Reasons to Override this Default

            - The project splits its verification across several jobs that must each pass, such as
              a build, a test suite, and a lint run reported separately, in which case the count
              should name each one that a merge is expected to wait for.
            - The repository holds content that no automation examines, such as documentation,
              assets, or configuration maintained by hand, where there is no check to require and
              the rule would block every pull request. Such a project can request a count of 0 so
              that the rule is required to stay off.
            - The named checks have diverged from the ones the repository runs. The rule names
              checks by the name they report under, so a renamed job leaves the ruleset waiting on
              a check that will never report, which blocks every pull request until the ruleset is
              edited.
            - Verification is enforced through a different mechanism, such as requiring successful
              deployments to an environment, which exercises the change in place rather than
              reporting on it through a status check.

            Note that the rule gates the merge on the checks it names rather than on every check
            that runs. A workflow whose name is absent from the ruleset reports its failure on the
            pull request without preventing the merge.

            Note also that a ruleset may pair this rule with **Require branches to be up to date
            before merging**, which is what makes a check run against the code as it will exist
            after the merge. Without it, a check that passed against an older base can be carried
            into a merge whose result was never tested.

            Note also that actors granted bypass permission on the ruleset may merge with checks
            failing, so the rule describes the path that contributors take rather than one that
            cannot be circumvented.
            """,
        )

        # The endpoint reports one rule per ruleset that applies to the branch, so checks named by
        # any matching rule count toward the total.
        status_check_rules = [rule for rule in rules if rule.get("type") == RULE_TYPE]

        checks: list[dict[str, object]] = []

        for rule in status_check_rules:
            parameters = cast(dict[str, object], rule.get("parameters") or {})
            checks += cast(
                list[dict[str, object]],
                parameters.get("required_status_checks") or [],
            )

        # A rule that must name no checks is a rule that must not be present, since one that names
        # none is enabled but inert.
        if acceptable_value == 0:
            if not status_check_rules:
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
                3) Clear the **Require status checks to pass** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset requires status checks to pass, but the requirement specifies that it must not.",
                resolution,
                rationale,
                self,
                module,
            )

        # The rule being absent and the rule naming too few checks are fixed by different actions,
        # so they are reported separately rather than as one count that happens to be zero.
        if not status_check_rules:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Check the **Require status checks to pass** checkbox in the **Branch rules** section.
                4) Add at least {acceptable_value} status check(s) beneath that checkbox.
                5) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                "The ruleset does not require status checks to pass.",
                resolution,
                rationale,
                self,
                module,
            )

        if len(checks) < acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            # The rule is already enabled, so the resolution names the checks to add rather than
            # directing the user to the checkbox.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Add at least {acceptable_value} status check(s) beneath the **Require status checks to pass** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The ruleset requires {len(checks)} status check(s), but the requirement specifies it must be at least {acceptable_value}.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
