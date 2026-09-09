import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_successful_deployments import (
    RequireSuccessfulDeploymentsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DEPLOYMENTS_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
        This requirement is not included by default because the rule presumes that the repository
        defines deployment environments and deploys to them from a pull request, which is a
        property of the project rather than something that can be inferred from the ruleset.

        When included, the default behavior is to require that a ruleset mandates successful
        deployments to at least 1 environment(s).

        ## Reasons for this Default

        - A project that includes this requirement has stated that its changes are expected to
          reach a deployment environment before they merge, so the rule is what makes that
          expectation hold for every pull request rather than only the ones a contributor
          remembers to deploy.
        - A deployment exercises the change in place. Infrastructure, database migrations, and
          configuration are the cases a test suite describes least well, and a deployment that
          fails against them is evidence no status check would have produced.
        - The rule has no effect unless the ruleset names at least one environment, so a minimum
          of 1 is the fewest that makes the rule do anything. A ruleset that enables
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
          request is open and the rule would block every one of them. Such a project can invert
          the expectation so that the rule is required to stay off.

        Note that the rule gates the merge rather than the release. A deployment that succeeds
        against the head of a pull request says nothing about the merge result, so it is a weaker
        signal than deploying from the base branch after the merge has landed.
        """,
)


# ----------------------------------------------------------------------
_REQUIRED_DEPLOYMENTS_RULE = {
    "type": "required_deployments",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {"required_deployment_environments": ["staging"]},
}

_TWO_ENVIRONMENTS_RULE = {
    **_REQUIRED_DEPLOYMENTS_RULE,
    "parameters": {"required_deployment_environments": ["staging", "production"]},
}

_NO_ENVIRONMENTS_RULE = {
    **_REQUIRED_DEPLOYMENTS_RULE,
    "parameters": {"required_deployment_environments": []},
}

_OTHER_RULE = {
    "type": "deletion",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequireSuccessfulDeploymentsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    value: int = 1,
    prohibit: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireSuccessfulDeploymentsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"include": True, "value": value, "prohibit": prohibit},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireSuccessfulDeploymentsRequirement()

    assert requirement.name == "RequireSuccessfulDeployments"
    assert (
        requirement.description
        == "Validates whether a ruleset requires changes to deploy successfully to named environments before branches matching its pattern can be merged."
    )
    assert requirement.requires_explicit_include is True


# ----------------------------------------------------------------------
# The requirement is opt-in, so the framework offers an 'include' flag rather than a 'skip' flag.
def test_GetParameters():
    parameters = RequireSuccessfulDeploymentsRequirement().GetParameters()

    assert list(parameters.keys()) == ["include", "prohibit", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 1
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "value"),
    [
        ([_REQUIRED_DEPLOYMENTS_RULE], 1),
        ([_TWO_ENVIRONMENTS_RULE], 1),
        ([_TWO_ENVIRONMENTS_RULE], 2),
        ([_OTHER_RULE, _REQUIRED_DEPLOYMENTS_RULE], 1),
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
    [[_REQUIRED_DEPLOYMENTS_RULE], [], [_OTHER_RULE]],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# A single rationale describes the requirement, so neither the requested count nor the inverted
# expectation changes it.
@pytest.mark.parametrize("value", [1, 3])
@pytest.mark.parametrize("prohibit", [False, True])
def test_RationaleIsInvariant(value, prohibit):
    result = _Evaluate([_TWO_ENVIRONMENTS_RULE], value=value, prohibit=prohibit)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# required deployments rule is one whose checkbox is not checked at all.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DeploymentsNotRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The ruleset does not require successful deployments."


# ----------------------------------------------------------------------
# An unchecked checkbox is reported as such no matter how many environments were requested, since
# the count is not what is wrong.
def test_DeploymentsNotRequiredWithHigherValue():
    result = _Evaluate([], value=3)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The ruleset does not require successful deployments."


# ----------------------------------------------------------------------
# The resolution directs the user to the checkbox, because the rule is absent rather than merely
# under-populated.
def test_DeploymentsNotRequiredResolution():
    result = _Evaluate([])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Select at least 1 environment(s) beneath that checkbox.
        5) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DEPLOYMENTS_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The rule gates a merge on the environments it names, so a rule that names none is enabled but
# cannot block anything. The checkbox is checked, so this is reported as a count rather than as an
# absent rule.
def test_RuleWithoutEnvironments():
    result = _Evaluate([_NO_ENVIRONMENTS_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires successful deployments to 0 environment(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# The rule is already enabled, so the resolution names the environments to add rather than
# directing the user to the checkbox.
def test_RuleWithoutEnvironmentsResolution():
    result = _Evaluate([_NO_ENVIRONMENTS_RULE])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Select at least 1 environment(s) beneath the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DEPLOYMENTS_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The environments are absent from a rule whose parameters are missing or empty, which is treated
# the same as a rule that names none rather than raising.
@pytest.mark.parametrize("parameters", [{}, {"required_deployment_environments": None}])
def test_RuleWithoutEnvironmentParameters(parameters):
    result = _Evaluate(
        [{**_REQUIRED_DEPLOYMENTS_RULE, "parameters": parameters}],
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires successful deployments to 0 environment(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# The count is a minimum, so naming fewer environments than requested is an error even though the
# rule is enabled.
def test_FewerEnvironmentsThanRequested():
    result = _Evaluate([_REQUIRED_DEPLOYMENTS_RULE], value=2)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires successful deployments to 1 environment(s), but the requirement specifies it must be at least 2."
    )


# ----------------------------------------------------------------------
# The count is a minimum rather than an exact value, so naming more environments than requested
# satisfies the requirement.
def test_MoreEnvironmentsThanRequested():
    result = _Evaluate([_TWO_ENVIRONMENTS_RULE], value=1)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# Environments named by any matching rule count toward the total, since the endpoint reports one
# rule per ruleset that applies to the branch.
def test_EnvironmentsAcrossMultipleRules():
    result = _Evaluate(
        [_NO_ENVIRONMENTS_RULE, _REQUIRED_DEPLOYMENTS_RULE],
        value=1,
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The resolution names the requested count rather than a fixed one, so it tells the user how many
# environments to select.
def test_ErrorResolutionUsesValue():
    result = _Evaluate([_REQUIRED_DEPLOYMENTS_RULE], value=3)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Select at least 3 environment(s) beneath the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DEPLOYMENTS_DOCUMENTATION_URL})
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
# 'prohibit' inverts the expectation, so an absent rule is what satisfies the requirement.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_ProhibitMatching(response):
    result = _Evaluate(response, prohibit=True)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "response",
    [[_REQUIRED_DEPLOYMENTS_RULE], [_TWO_ENVIRONMENTS_RULE], [_NO_ENVIRONMENTS_RULE]],
)
def test_ProhibitWhenRequired(response):
    result = _Evaluate(response, prohibit=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires successful deployments, but the requirement specifies that it must not."
    )


# ----------------------------------------------------------------------
# The resolution clears the checkbox rather than naming environments, since the rule is expected to
# be absent entirely.
def test_ProhibitResolution():
    result = _Evaluate([_REQUIRED_DEPLOYMENTS_RULE], prohibit=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DEPLOYMENTS_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The count describes how much the rule must require, so it is not consulted when the rule is
# expected to be absent.
@pytest.mark.parametrize("value", [1, 5])
def test_ProhibitIgnoresValue(value):
    result = _Evaluate([_TWO_ENVIRONMENTS_RULE], value=value, prohibit=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires successful deployments, but the requirement specifies that it must not."
    )


# ----------------------------------------------------------------------
# The requirement is opt-in, so it does not run unless the user includes it.
def test_NotIncluded():
    requirement = RequireSuccessfulDeploymentsRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"include": False, "value": 1, "prohibit": False},
    )

    assert result.result == EvaluateResultValue.Skipped
