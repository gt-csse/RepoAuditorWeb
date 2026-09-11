import textwrap

from enum import StrEnum
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from collections.abc import Iterable

    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule; the allowed merge methods are a parameter of that rule rather than a rule of its
# own.
RULE_TYPE = "pull_request"


# ----------------------------------------------------------------------
class Values(StrEnum):
    """Enumeration of the merge methods that a ruleset can allow."""

    Merge = "merge"
    Squash = "squash"
    Rebase = "rebase"


# The label GitHub displays for each method in the ruleset's checkbox list, which is what the
# resolution asks the user to select rather than the value the API reports.
UI_LABELS: dict[Values, str] = {
    Values.Merge: "Merge",
    Values.Squash: "Squash",
    Values.Rebase: "Rebase",
}


# ----------------------------------------------------------------------
class AllowedMergeMethodsRequirement(Requirement):
    """Validates which merge methods a ruleset permits when a pull request targeting branches matching its pattern is merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "AllowedMergeMethods",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The setting is a set of checkboxes rather than a single choice, so the parameter is
            # repeatable and names the methods to allow rather than toggling one of them.
            "value": TyperParameter(
                list[Values],
                [Values.Merge],
                OptionInfo(
                    help="Merge method the ruleset allows; repeat the option to allow more than one.",
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

        # The endpoint reports only the rules that apply, so the absence of the pull request rule
        # means the branch accepts direct pushes.
        pull_request_rule = next((rule for rule in rules if rule.get("type") == RULE_TYPE), None)

        # The methods are a setting of the pull request rule, so they govern nothing on a branch
        # that does not require one. Reporting a failure here would restate the absence of the pull
        # request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so no merge method is imposed on the branch.",
                None,
                None,
                self,
                module,
            )

        # A method named more than once on the command line describes the same set, and the order
        # the checkboxes are listed in carries no meaning, so both are normalized away.
        acceptable_values = _Normalize(cast(list[Values], requirement_data["value"]))

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset allows the merge commit method alone.

            Note that this differs from GitHub's own default when the pull request rule is added to
            a branch ruleset, where all three methods are allowed.

            ## Reasons for this Default

            - The merge commit is the only method that lands the commits that were reviewed and
              tested. Squashing rewrites a branch into a new commit and rebasing replays each commit
              onto a base that has moved, so in both cases the object that reaches the branch is not
              the object the status checks ran against.
            - It is the only method that preserves a contributor's signatures. A squash discards the
              authored commits in favor of one signed with GitHub's web-flow key, and a rebase lands
              commits that nothing signs at all, so neither history retains a signature attesting to
              who wrote the code.
            - Restricting the branch to one method is what makes its history uniform. Leaving the
              choice to whoever clicks merge produces a branch whose shape depends on who landed
              each change, so tooling that reads the history has to accommodate every method the
              ruleset permits.
            - The ruleset is where the restriction holds for the branch that matters. The
              repository's own merge method checkboxes apply to every branch at once, so a project
              that wants a strict default branch alongside a permissive release or integration
              branch can express that only here.
            - Narrowing the methods costs a contributor nothing. The pull request is merged the same
              way regardless of which methods are permitted; the rule removes options from the merge
              button rather than adding a step to the process.

            ## Reasons to Override this Default

            - The project treats a pull request as one logical change and wants a single commit per
              change on the branch, which is what squashing produces; this matters most where
              branches accumulate fixup and work-in-progress commits that carry no meaning once the
              review is over.
            - The ruleset also requires a linear history, which no merge commit can satisfy. Such a
              ruleset must allow squashing, rebasing, or both, and allowing the merge commit alone
              leaves a merge button that the linear history rule rejects.
            - The project curates its branches so that each commit is a meaningful, independently
              reviewable step, and regards collapsing them into one as the greater loss (`rebase`).
            - Contributors need the choice because the right method depends on the change, such as a
              repository that squashes routine work but merges a long-running branch whose commits
              are worth keeping.

            Note that a ruleset can only narrow what the repository already allows, so a method
            selected here is still unavailable unless the corresponding **Pull Requests** checkbox
            in the repository's settings is also enabled. A ruleset that names a method the
            repository disallows blocks the merge rather than enabling the method.

            Note also that merge queues do not honor this setting, since the queue controls the
            method used for the merges it performs.

            Note also that actors granted bypass permission on the ruleset may merge using a method
            it excludes, so the setting describes the path that contributors take rather than one
            that cannot be circumvented.
            """,
        )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})

        # GitHub reports every method the rule allows, so a rule that omits the setting is not
        # restricting the branch to any particular method.
        merge_methods_value = _Normalize(
            Values(method) for method in cast(list[str], parameters.get("allowed_merge_methods") or [])
        )

        if merge_methods_value != acceptable_values:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            expected_labels = ", ".join(f"**{UI_LABELS[value]}**" for value in acceptable_values)

            # The requirement does not apply unless the pull request rule is enabled, so the
            # checkboxes are already available and the resolution does not need to enable the rule.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) Check {expected_labels} beneath **Require a pull request before merging** in the **Branch rules** section, clearing the methods that are not listed.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            # The methods are reported as the labels shown in the ruleset rather than the values the
            # API uses, because the labels are what the resolution asks the user to select.
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{_FormatValues(merge_methods_value)}', but the requirement specifies it must be '{_FormatValues(acceptable_values)}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _Normalize(values: Iterable[Values]) -> list[Values]:
    """Return the distinct methods in the order the ruleset lists their checkboxes."""

    distinct_values = set(values)

    # The set is reported and resolved in the order the checkboxes appear in the ruleset rather than
    # alphabetically, so that what is read matches what is seen on the settings page.
    return [value for value in Values if value in distinct_values]


# ----------------------------------------------------------------------
def _FormatValues(values: list[Values]) -> str:
    """Return the UI labels for a set of methods, naming the empty set rather than rendering it blank."""

    return ", ".join(UI_LABELS[value] for value in values) if values else "<none>"
