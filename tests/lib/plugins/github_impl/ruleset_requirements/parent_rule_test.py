from typing import cast

import pytest

from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements import parent_rule
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement


# ----------------------------------------------------------------------
_PULL_REQUEST_RULE: dict[str, object] = {
    "type": "pull_request",
    "parameters": {"required_approving_review_count": 2},
}


# ----------------------------------------------------------------------
_OTHER_RULE: dict[str, object] = {"type": "deletion", "parameters": {}}


# ----------------------------------------------------------------------
def test_PullRequestRuleType():
    assert parent_rule.PULL_REQUEST_RULE_TYPE == "pull_request"


# ----------------------------------------------------------------------
class TestGetNotOwnedByOrganizationResult:
    # ----------------------------------------------------------------------
    def test_OwnedByOrganization(self):
        assert (
            parent_rule.GetNotOwnedByOrganizationResult(
                {"owner_type": "Organization"},
                "The context.",
                cast(Requirement, None),
                cast(Module, None),
            )
            is None
        )

    # ----------------------------------------------------------------------
    def test_OwnedByUser(self):
        requirement = cast(Requirement, object())
        module = cast(Module, object())

        result = parent_rule.GetNotOwnedByOrganizationResult(
            {"owner_type": "User"},
            "The context.",
            requirement,
            module,
        )

        assert result == EvaluateResult(
            EvaluateResultValue.DoesNotApply,
            "The context.",
            None,
            None,
            requirement,
            module,
        )


# ----------------------------------------------------------------------
class TestGetRuleParameters:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("evaluate_all", [True, False])
    def test_RulePresent(self, evaluate_all):
        assert parent_rule.GetRuleParameters(
            {"response": [_OTHER_RULE, _PULL_REQUEST_RULE]},
            "pull_request",
            evaluate_all=evaluate_all,
        ) == [{"required_approving_review_count": 2}]

    # ----------------------------------------------------------------------
    # The endpoint reports one rule per ruleset that applies to the branch, so each is returned for
    # the caller to combine.
    def test_EveryMatchingRuleIsReturned(self):
        assert parent_rule.GetRuleParameters(
            {
                "response": [
                    _PULL_REQUEST_RULE,
                    _OTHER_RULE,
                    {"type": "pull_request", "parameters": {"required_approving_review_count": 3}},
                ],
            },
            "pull_request",
            evaluate_all=False,
        ) == [{"required_approving_review_count": 2}, {"required_approving_review_count": 3}]

    # ----------------------------------------------------------------------
    def test_RuleWithoutParameters(self):
        assert parent_rule.GetRuleParameters(
            {"response": [{"type": "pull_request"}]},
            "pull_request",
            evaluate_all=False,
        ) == [{}]

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
    def test_RuleAbsent(self, response):
        assert (
            parent_rule.GetRuleParameters({"response": response}, "pull_request", evaluate_all=False) is None
        )

    # ----------------------------------------------------------------------
    # An absent rule is reported as one carrying no parameters, which is the state GitHub reports
    # once the rule is enabled without any of its settings being selected.
    @pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
    def test_RuleAbsentWhenEvaluatingAll(self, response):
        assert parent_rule.GetRuleParameters({"response": response}, "pull_request", evaluate_all=True) == [
            {}
        ]

    # ----------------------------------------------------------------------
    def test_RuleTypeIsHonored(self):
        assert (
            parent_rule.GetRuleParameters(
                {"response": [_PULL_REQUEST_RULE]},
                "required_status_checks",
                evaluate_all=False,
            )
            is None
        )

    # ----------------------------------------------------------------------
    # A setting that GitHub selects when the rule is enabled must be evaluated against that
    # selection rather than against its absence.
    def test_SynthesizedRuleCarriesDefaultParameters(self):
        assert parent_rule.GetRuleParameters(
            {"response": []},
            "pull_request",
            evaluate_all=True,
            default_parameters={"allowed_merge_methods": ["merge", "squash", "rebase"]},
        ) == [{"allowed_merge_methods": ["merge", "squash", "rebase"]}]

    # ----------------------------------------------------------------------
    # The defaults describe a rule that had to be synthesized, so a rule the endpoint reported is
    # returned as-is.
    def test_DefaultParametersIgnoredWhenRulePresent(self):
        assert parent_rule.GetRuleParameters(
            {"response": [_PULL_REQUEST_RULE]},
            "pull_request",
            evaluate_all=True,
            default_parameters={"allowed_merge_methods": ["merge"]},
        ) == [{"required_approving_review_count": 2}]

    # ----------------------------------------------------------------------
    def test_DefaultParametersIgnoredWhenNotEvaluatingAll(self):
        assert (
            parent_rule.GetRuleParameters(
                {"response": []},
                "pull_request",
                evaluate_all=False,
                default_parameters={"allowed_merge_methods": ["merge"]},
            )
            is None
        )


# ----------------------------------------------------------------------
class TestGetPullRequestRuleResolutionPrefix:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("evaluate_all", [True, False])
    def test_RulePresent(self, evaluate_all):
        assert parent_rule.GetPullRequestRuleResolutionPrefix(
            {"response": [_PULL_REQUEST_RULE]},
            evaluate_all=evaluate_all,
        ) == (
            "3) In the **Branch rules** section, find **Require a pull request before merging**, and click **Show additional settings**."
        )

    # ----------------------------------------------------------------------
    # The rule must be enabled before the setting nested within it can be selected, so the step
    # that enables it replaces the one that reveals the additional settings.
    @pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
    def test_RuleAbsent(self, response):
        assert parent_rule.GetPullRequestRuleResolutionPrefix(
            {"response": response},
            evaluate_all=True,
        ) == (
            "3) Check the **Require a pull request before merging** checkbox in the **Branch rules** section."
        )


# ----------------------------------------------------------------------
class TestGetStatusChecksResolutionPrefix:
    # ----------------------------------------------------------------------
    def test_ChecksPresent(self):
        assert parent_rule.GetStatusChecksResolutionPrefix([{"context": "my-check"}]) == (
            "3) In the **Branch rules** section, find **Require status checks to pass**, and click **Show additional settings**."
        )

    # ----------------------------------------------------------------------
    # GitHub does not apply the setting until the rule names a check, so the step names both the
    # rule and the check rather than only where the setting is found.
    def test_ChecksAbsent(self):
        assert parent_rule.GetStatusChecksResolutionPrefix([]) == (
            "3) Check the **Require status checks to pass** checkbox in the **Branch rules** section "
            "and add at least one status check beneath it."
        )
