"""Functionality for requirements whose setting is nested within another ruleset rule."""

from typing import cast, TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.requirement import Markdown


# ----------------------------------------------------------------------
# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule, which hosts the settings that several requirements validate.
PULL_REQUEST_RULE_TYPE = "pull_request"


# ----------------------------------------------------------------------
def GetRule(
    query_data: dict[str, object],
    rule_type: str,
    *,
    evaluate_all: bool,
    default_parameters: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Return the rule of 'rule_type' that applies to the branch, or None if the requirement does not apply.

    The endpoint reports only the rules that apply, so an absent rule leaves the nested setting
    governing nothing and the requirement reports that it does not apply. When the user asks for
    every requirement to be evaluated, an absent rule is instead treated as one that GitHub has just
    enabled, which is what allows the nested setting to be reported as a failure in the same run as
    the rule itself.

    'default_parameters' are the parameters that GitHub populates when the rule is enabled. Most
    settings are absent from a freshly enabled rule and their readers already treat absence as the
    unselected state, so the default is to carry no parameters; a setting that GitHub selects on
    the caller's behalf must name it here to be reported against the value the user would land on.
    """

    rules = cast(list[dict[str, object]], query_data["response"])

    rule = next((rule for rule in rules if rule.get("type") == rule_type), None)

    if rule is None and evaluate_all:
        return {"type": rule_type, "parameters": default_parameters or {}}

    return rule


# ----------------------------------------------------------------------
def GetPullRequestRuleResolutionPrefix(
    query_data: dict[str, object],
    *,
    evaluate_all: bool,
) -> Markdown:
    """Return the resolution steps that reach the nested settings of the pull request rule.

    The steps that follow are numbered from 4, so an absent rule contributes the step that enables
    it in place of the one that reveals the settings of a rule that is already enabled.
    """

    rules = cast(list[dict[str, object]], query_data["response"])

    if any(rule.get("type") == PULL_REQUEST_RULE_TYPE for rule in rules):
        return "3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section."

    # The requirement is only reached with the rule absent when every requirement is being
    # evaluated, where enabling the rule is what makes the nested setting reachable. The step is
    # stated here rather than left to RequirePullRequests because the user works through one
    # requirement's resolution at a time.
    assert evaluate_all

    return "3) Check the **Require a pull request before merging** checkbox in the **Branch rules** section."


# ----------------------------------------------------------------------
def GetStatusChecksResolutionPrefix(
    checks: list[dict[str, object]],
    *,
    evaluate_all: bool,
) -> Markdown:
    """Return the resolution steps that reach the nested settings of the status checks rule.

    The steps that follow are numbered from 4, so a rule that names no check contributes the steps
    that add one in place of the one that reveals the settings of a rule already naming checks.
    """

    if checks:
        return "3) Click **Show additional settings** beneath **Require status checks to pass** in the **Branch rules** section."

    # GitHub does not apply the setting until the rule names a check, so the resolution states what
    # makes the checkbox take effect rather than only where to find it.
    assert evaluate_all

    return (
        "3) Check the **Require status checks to pass** checkbox in the **Branch rules** section "
        "and add at least one status check beneath it."
    )
