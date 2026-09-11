import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_code_scanning_results import (
    RequireCodeScanningResultsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_CODE_SCANNING_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-code-scanning-results"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset mandates results from at least
    1 code scanning tool(s) before merging.

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
      1 is the fewest that makes the rule do anything. A ruleset that enables
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


# ----------------------------------------------------------------------
_CODE_SCANNING_RULE = {
    "type": "code_scanning",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {
        "code_scanning_tools": [
            {
                "tool": "CodeQL",
                "alerts_threshold": "errors",
                "security_alerts_threshold": "high_or_higher",
            },
        ],
    },
}

_TWO_TOOLS_RULE = {
    **_CODE_SCANNING_RULE,
    "parameters": {
        "code_scanning_tools": [
            {
                "tool": "CodeQL",
                "alerts_threshold": "errors",
                "security_alerts_threshold": "high_or_higher",
            },
            {
                "tool": "my-scanner",
                "alerts_threshold": "errors_and_warnings",
                "security_alerts_threshold": "medium_or_higher",
            },
        ],
    },
}

_NO_TOOLS_RULE = {
    **_CODE_SCANNING_RULE,
    "parameters": {"code_scanning_tools": []},
}

_OTHER_RULE = {
    "type": "deletion",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequireCodeScanningResultsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    value: int = 1,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireCodeScanningResultsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "value": value},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireCodeScanningResultsRequirement()

    assert requirement.name == "RequireCodeScanningResults"
    assert (
        requirement.description
        == "Validates whether a ruleset requires named code scanning tools to report results below their alert thresholds before branches matching its pattern can be merged."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
# The requirement runs by default, so the framework offers a 'skip' flag rather than an 'include'
# flag.
def test_GetParameters():
    parameters = RequireCodeScanningResultsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 1


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "value"),
    [
        ([_CODE_SCANNING_RULE], 1),
        ([_TWO_TOOLS_RULE], 1),
        ([_TWO_TOOLS_RULE], 2),
        ([_OTHER_RULE, _CODE_SCANNING_RULE], 1),
    ],
)
def test_MatchingValue(response, value):
    result = _Evaluate(response, value=value)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the requirement regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize(
    "response",
    [[_CODE_SCANNING_RULE], [], [_OTHER_RULE]],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# A single rationale describes the requirement, so the requested count does not change it,
# including the count of 0 that inverts the expectation.
@pytest.mark.parametrize("value", [0, 1, 3])
def test_RationaleIsInvariant(value):
    result = _Evaluate([_TWO_TOOLS_RULE], value=value)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the code
# scanning rule is one whose checkbox is not checked at all.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_CodeScanningNotRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The ruleset does not require code scanning results."


# ----------------------------------------------------------------------
# An unchecked checkbox is reported as such no matter how many tools were requested, since the
# count is not what is wrong.
def test_CodeScanningNotRequiredWithHigherValue():
    result = _Evaluate([], value=3)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The ruleset does not require code scanning results."


# ----------------------------------------------------------------------
# The resolution directs the user to the checkbox, because the rule is absent rather than merely
# under-populated.
def test_CodeScanningNotRequiredResolution():
    result = _Evaluate([])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require code scanning results** checkbox in the **Branch rules** section.
        4) Add at least 1 code scanning tool(s) beneath that checkbox.
        5) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_CODE_SCANNING_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The rule gates a merge on the tools it names, so a rule that names none is enabled but cannot
# block anything. The checkbox is checked, so this is reported as a count rather than as an absent
# rule.
def test_RuleWithoutTools():
    result = _Evaluate([_NO_TOOLS_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires 0 code scanning tool(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# The rule is already enabled, so the resolution names the tools to add rather than directing the
# user to the checkbox.
def test_RuleWithoutToolsResolution():
    result = _Evaluate([_NO_TOOLS_RULE])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Add at least 1 code scanning tool(s) beneath the **Require code scanning results** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_CODE_SCANNING_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The tools are absent from a rule whose parameters are missing or empty, which is treated the same
# as a rule that names none rather than raising.
@pytest.mark.parametrize("parameters", [{}, {"code_scanning_tools": None}])
def test_RuleWithoutToolParameters(parameters):
    result = _Evaluate(
        [{**_CODE_SCANNING_RULE, "parameters": parameters}],
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires 0 code scanning tool(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# The count is a minimum, so naming fewer tools than requested is an error even though the rule is
# enabled.
def test_FewerToolsThanRequested():
    result = _Evaluate([_CODE_SCANNING_RULE], value=2)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires 1 code scanning tool(s), but the requirement specifies it must be at least 2."
    )


# ----------------------------------------------------------------------
# The count is a minimum rather than an exact value, so naming more tools than requested satisfies
# the requirement.
def test_MoreToolsThanRequested():
    result = _Evaluate([_TWO_TOOLS_RULE], value=1)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# Tools named by any matching rule count toward the total, since the endpoint reports one rule per
# ruleset that applies to the branch.
def test_ToolsAcrossMultipleRules():
    result = _Evaluate([_NO_TOOLS_RULE, _CODE_SCANNING_RULE], value=1)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The requirement counts the tools the rule names rather than inspecting their thresholds, so a
# tool that blocks nothing still satisfies the count.
def test_ToolWithoutThresholds():
    result = _Evaluate(
        [
            {
                **_CODE_SCANNING_RULE,
                "parameters": {
                    "code_scanning_tools": [
                        {
                            "tool": "CodeQL",
                            "alerts_threshold": "none",
                            "security_alerts_threshold": "none",
                        },
                    ],
                },
            },
        ],
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The resolution names the requested count rather than a fixed one, so it tells the user how many
# tools to add.
def test_ErrorResolutionUsesValue():
    result = _Evaluate([_CODE_SCANNING_RULE], value=3)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Add at least 3 code scanning tool(s) beneath the **Require code scanning results** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_CODE_SCANNING_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate([], url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
# A count of 0 inverts the expectation, so an absent rule is what satisfies the requirement.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_ZeroMatching(response):
    result = _Evaluate(response, value=0)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# A rule that names no tools is enabled but inert, so it is still reported as present rather than
# as satisfying a count of 0.
@pytest.mark.parametrize(
    "response",
    [[_CODE_SCANNING_RULE], [_TWO_TOOLS_RULE], [_NO_TOOLS_RULE]],
)
def test_ZeroWhenRequired(response):
    result = _Evaluate(response, value=0)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires code scanning results, but the requirement specifies that it must not."
    )


# ----------------------------------------------------------------------
# The resolution clears the checkbox rather than naming tools, since the rule is expected to be
# absent entirely.
def test_ZeroResolution():
    result = _Evaluate([_CODE_SCANNING_RULE], value=0)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require code scanning results** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_CODE_SCANNING_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The requirement runs by default, so it is only skipped when the user asks for it.
def test_Skipped():
    requirement = RequireCodeScanningResultsRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"skip": True, "value": 1},
    )

    assert result.result == EvaluateResultValue.Skipped
