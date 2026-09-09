import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_successful_deployments import (
    RequireSuccessfulDeploymentsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-deployments-to-succeed-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
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


# ----------------------------------------------------------------------
_REQUIRED_DEPLOYMENTS_RULE = {
    "type": "required_deployments",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {"required_deployment_environments": ["staging"]},
}

_OTHER_RULE = {
    "type": "deletion",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}

_NO_ENVIRONMENTS_RULE = {
    **_REQUIRED_DEPLOYMENTS_RULE,
    "parameters": {"required_deployment_environments": []},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequireSuccessfulDeploymentsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    require: bool = False,
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
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireSuccessfulDeploymentsRequirement()

    assert requirement.name == "RequireSuccessfulDeployments"
    assert (
        requirement.description
        == "Validates whether a ruleset requires changes to deploy successfully to named environments before branches matching its pattern can be merged."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireSuccessfulDeploymentsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "require"),
    [
        ([], False),
        ([_OTHER_RULE], False),
        ([_REQUIRED_DEPLOYMENTS_RULE], True),
        ([_OTHER_RULE, _REQUIRED_DEPLOYMENTS_RULE], True),
    ],
)
def test_MatchingValue(response, require):
    result = _Evaluate(response, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize("response", [[_REQUIRED_DEPLOYMENTS_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_RequiredWhenNotRequested():
    result = _Evaluate([_REQUIRED_DEPLOYMENTS_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# required deployments rule is one that can be merged without a successful deployment.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_NotRequiredWhenRequested(response):
    result = _Evaluate(response, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# The rule gates a merge on the environments it names, so a rule that names none is enabled but
# cannot block anything.
def test_RuleWithoutEnvironments():
    result = _Evaluate([_NO_ENVIRONMENTS_RULE], require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires successful deployments, but does not name any environments to deploy to."
    )


# ----------------------------------------------------------------------
# The environments are absent from a rule whose parameters are missing or empty, which is treated
# the same as a rule that names none rather than raising.
@pytest.mark.parametrize(
    "parameters",
    [{}, {"required_deployment_environments": None}],
)
def test_RuleWithoutEnvironmentParameters(parameters):
    result = _Evaluate([{**_REQUIRED_DEPLOYMENTS_RULE, "parameters": parameters}], require=True)

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
# The resolution directs the user to name an environment rather than to toggle the rule, because the
# rule is already present as requested.
def test_RuleWithoutEnvironmentsResolution():
    result = _Evaluate([_NO_ENVIRONMENTS_RULE], require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Select at least one environment under the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A rule that names no environments is still present, so a user who wants the rule absent gets the
# mismatch rather than the missing-environment error.
def test_RuleWithoutEnvironmentsWhenNotRequested():
    result = _Evaluate([_NO_ENVIRONMENTS_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# Environments named by any matching rule satisfy the requirement, since the endpoint reports one
# rule per ruleset that applies to the branch.
def test_EnvironmentsAcrossMultipleRules():
    result = _Evaluate([_NO_ENVIRONMENTS_RULE, _REQUIRED_DEPLOYMENTS_RULE], require=True)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_REQUIRED_DEPLOYMENTS_RULE])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to set the rule when successful deployments must be required.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate([], require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require deployments to succeed** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_REQUIRED_DEPLOYMENTS_RULE], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        [_REQUIRED_DEPLOYMENTS_RULE],
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireSuccessfulDeploymentsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
