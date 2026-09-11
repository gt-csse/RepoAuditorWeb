import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require status checks to pass"
# rule; branch freshness is a parameter of that rule rather than a rule of its own.
RULE_TYPE = "required_status_checks"


# ----------------------------------------------------------------------
class RequireBranchesToBeUpToDateBeforeMergingRequirement(Requirement):
    """Validates whether a ruleset requires that a pull request branch is up to date with its base branch before merging, so that status checks run against the merged result."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireBranchesToBeUpToDateBeforeMerging",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the setting to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(
                    help="Require that branches are not required to be up to date before merging.",
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

        # The endpoint reports one rule per ruleset that applies to the branch, so the setting is
        # satisfied when any matching rule enables it.
        status_check_rules = [rule for rule in rules if rule.get("type") == RULE_TYPE]

        checks: list[dict[str, object]] = []

        for rule in status_check_rules:
            parameters = cast(dict[str, object], rule.get("parameters") or {})
            checks += cast(
                list[dict[str, object]],
                parameters.get("required_status_checks") or [],
            )

        # GitHub does not apply the setting unless the rule names a check to run, so it governs
        # nothing here. Reporting a failure would restate the state of the status checks rule, which
        # RequireStatusChecksToPass already covers.
        if not checks:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require any status checks to pass, so there are no check results that depend on the branch being up to date.",
                None,
                None,
                self,
                module,
            )

        strict_value = any(
            bool(
                cast(dict[str, object], rule.get("parameters") or {}).get(
                    "strict_required_status_checks_policy",
                ),
            )
            for rule in status_check_rules
        )

        acceptable_value = not cast(bool, requirement_data["prohibit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset requires branches to be up to date
            before merging.

            Note that this matches GitHub's own default when the status checks rule is added to a
            branch ruleset, where the checkbox is selected.

            ## Reasons for this Default

            - Without it, a required check reports on a commit that will never exist. The check runs
              against the topic branch as it was written, while the merge produces that branch
              combined with everything the base branch gained since, so the ruleset gates the merge
              on a result that describes different code than the one being merged.
            - The failure it prevents is the one that reaches the default branch. Two changes can
              each pass on their own and break once combined, so the branch goes red after a merge
              that the ruleset reported as green, and the breakage is found by whoever pulls next
              rather than by the author who introduced it.
            - The conflicts it catches are the ones git cannot see. A textual conflict already stops
              the merge, but a caller left behind by a renamed function, a signature that gained an
              argument, or a test that a new invariant invalidates all merge cleanly and fail only
              when something builds them together.
            - It is what makes the other rule's guarantee true. Requiring status checks establishes
              that a check passed, and this setting establishes that it passed against the code the
              merge produces, so together they say the default branch was verified rather than that
              some earlier version of it was.
            - The cost is a button. GitHub offers **Update branch** on a pull request that has
              fallen behind, and the re-run is the same check the project already requires, so the
              expense is waiting rather than work.

            ## Reasons to Override this Default

            - The repository uses a merge queue, which builds each pull request against the base
              branch and the entries queued ahead of it before merging. That establishes the same
              property at the moment of the merge, so requiring the branch to be current beforehand
              adds a round of updates that the queue makes redundant.
            - The base branch moves faster than the checks complete. Where merges land more often
              than a build takes to run, a branch can fall behind while its own checks are still
              running, and pull requests are updated and re-verified repeatedly without ever
              becoming mergeable.
            - The cost falls unevenly across contributors. Updating a branch requires push access to
              it, so a pull request from a fork can stall waiting on its author, and a long-lived
              branch pays for the update again on every merge that lands ahead of it.
            - The checks do not examine anything a merge could disturb. Where they read only the
              files the pull request changes, such as a lint run or a link check over documentation,
              the base branch moving does not change what they would report.

            Note that the setting has no effect unless the ruleset names at least one status check,
            since it governs which commit the required checks run against rather than requiring a
            check of its own.

            Note also that GitHub tests the branch for freshness when the merge is attempted rather
            than when the checks are run, so two pull requests that are both up to date can still
            race, and the second is sent back to be updated rather than merged on a stale result.

            Note also that actors granted bypass permission on the ruleset may merge a branch that
            has fallen behind, so the setting describes the path that contributors take rather than
            one that cannot be circumvented.
            """,
        )

        if strict_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            # The requirement does not apply unless the status checks rule names a check, so the
            # checkbox is already available and the resolution does not need to enable the rule.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require branches to be up to date before merging** checkbox beneath **Require status checks to pass** in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{strict_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
