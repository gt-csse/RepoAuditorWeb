import pytest

from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements import parent_rule


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
class TestGetRule:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("evaluate_all", [True, False])
    def test_RulePresent(self, evaluate_all):
        rule = parent_rule.GetRule(
            {"response": [_OTHER_RULE, _PULL_REQUEST_RULE]},
            "pull_request",
            evaluate_all=evaluate_all,
        )

        assert rule is _PULL_REQUEST_RULE

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
    def test_RuleAbsent(self, response):
        assert parent_rule.GetRule({"response": response}, "pull_request", evaluate_all=False) is None

    # ----------------------------------------------------------------------
    # An absent rule is reported as one carrying no parameters, which is the state GitHub reports
    # once the rule is enabled without any of its settings being selected.
    @pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
    def test_RuleAbsentWhenEvaluatingAll(self, response):
        assert parent_rule.GetRule({"response": response}, "pull_request", evaluate_all=True) == {
            "type": "pull_request",
            "parameters": {},
        }

    # ----------------------------------------------------------------------
    def test_RuleTypeIsHonored(self):
        response = [_PULL_REQUEST_RULE]

        assert (
            parent_rule.GetRule({"response": response}, "required_status_checks", evaluate_all=False) is None
        )

    # ----------------------------------------------------------------------
    def test_SynthesizedRuleUsesRequestedType(self):
        assert parent_rule.GetRule(
            {"response": []},
            "required_status_checks",
            evaluate_all=True,
        ) == {"type": "required_status_checks", "parameters": {}}

    # ----------------------------------------------------------------------
    # A setting that GitHub selects when the rule is enabled must be evaluated against that
    # selection rather than against its absence.
    def test_SynthesizedRuleCarriesDefaultParameters(self):
        assert parent_rule.GetRule(
            {"response": []},
            "pull_request",
            evaluate_all=True,
            default_parameters={"allowed_merge_methods": ["merge", "squash", "rebase"]},
        ) == {
            "type": "pull_request",
            "parameters": {"allowed_merge_methods": ["merge", "squash", "rebase"]},
        }

    # ----------------------------------------------------------------------
    # The defaults describe a rule that had to be synthesized, so a rule the endpoint reported is
    # returned as-is.
    def test_DefaultParametersIgnoredWhenRulePresent(self):
        assert (
            parent_rule.GetRule(
                {"response": [_PULL_REQUEST_RULE]},
                "pull_request",
                evaluate_all=True,
                default_parameters={"allowed_merge_methods": ["merge"]},
            )
            is _PULL_REQUEST_RULE
        )

    # ----------------------------------------------------------------------
    def test_DefaultParametersIgnoredWhenNotEvaluatingAll(self):
        assert (
            parent_rule.GetRule(
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
            "3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section."
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
    @pytest.mark.parametrize("evaluate_all", [True, False])
    def test_ChecksPresent(self, evaluate_all):
        assert parent_rule.GetStatusChecksResolutionPrefix(
            [{"context": "my-check"}],
            evaluate_all=evaluate_all,
        ) == (
            "3) Click **Show additional settings** beneath **Require status checks to pass** in the **Branch rules** section."
        )

    # ----------------------------------------------------------------------
    # GitHub does not apply the setting until the rule names a check, so the step names both the
    # rule and the check rather than only where the setting is found.
    def test_ChecksAbsent(self):
        assert parent_rule.GetStatusChecksResolutionPrefix([], evaluate_all=True) == (
            "3) Check the **Require status checks to pass** checkbox in the **Branch rules** section "
            "and add at least one status check beneath it."
        )
