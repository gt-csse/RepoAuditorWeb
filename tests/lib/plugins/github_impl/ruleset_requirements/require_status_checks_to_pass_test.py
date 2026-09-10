import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_status_checks_to_pass import (
    RequireStatusChecksToPassRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_STATUS_CHECKS_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset mandates at least 1
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
      1 is the fewest that makes the rule do anything. A ruleset that enables
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


# ----------------------------------------------------------------------
_REQUIRED_STATUS_CHECKS_RULE = {
    "type": "required_status_checks",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {
        "strict_required_status_checks_policy": True,
        "do_not_enforce_on_create": False,
        "required_status_checks": [{"context": "build", "integration_id": 15368}],
    },
}

_TWO_CHECKS_RULE = {
    **_REQUIRED_STATUS_CHECKS_RULE,
    "parameters": {
        "strict_required_status_checks_policy": True,
        "do_not_enforce_on_create": False,
        "required_status_checks": [
            {"context": "build", "integration_id": 15368},
            {"context": "test", "integration_id": 15368},
        ],
    },
}

_NO_CHECKS_RULE = {
    **_REQUIRED_STATUS_CHECKS_RULE,
    "parameters": {
        "strict_required_status_checks_policy": True,
        "do_not_enforce_on_create": False,
        "required_status_checks": [],
    },
}

_OTHER_RULE = {
    "type": "deletion",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequireStatusChecksToPassRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    value: int = 1,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireStatusChecksToPassRequirement()

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
    requirement = RequireStatusChecksToPassRequirement()

    assert requirement.name == "RequireStatusChecksToPass"
    assert (
        requirement.description
        == "Validates whether a ruleset requires named status checks to pass before changes to branches matching its pattern can be merged."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
# The requirement runs by default, so the framework offers a 'skip' flag rather than an 'include'
# flag.
def test_GetParameters():
    parameters = RequireStatusChecksToPassRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 1


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "value"),
    [
        ([_REQUIRED_STATUS_CHECKS_RULE], 1),
        ([_TWO_CHECKS_RULE], 1),
        ([_TWO_CHECKS_RULE], 2),
        ([_OTHER_RULE, _REQUIRED_STATUS_CHECKS_RULE], 1),
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
    [[_REQUIRED_STATUS_CHECKS_RULE], [], [_OTHER_RULE]],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# A single rationale describes the requirement, so the requested count does not change it,
# including the count of 0 that inverts the expectation.
@pytest.mark.parametrize("value", [0, 1, 3])
def test_RationaleIsInvariant(value):
    result = _Evaluate([_TWO_CHECKS_RULE], value=value)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# required status checks rule is one whose checkbox is not checked at all.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_StatusChecksNotRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The ruleset does not require status checks to pass."


# ----------------------------------------------------------------------
# An unchecked checkbox is reported as such no matter how many checks were requested, since the
# count is not what is wrong.
def test_StatusChecksNotRequiredWithHigherValue():
    result = _Evaluate([], value=3)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The ruleset does not require status checks to pass."


# ----------------------------------------------------------------------
# The resolution directs the user to the checkbox, because the rule is absent rather than merely
# under-populated.
def test_StatusChecksNotRequiredResolution():
    result = _Evaluate([])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require status checks to pass** checkbox in the **Branch rules** section.
        4) Add at least 1 status check(s) beneath that checkbox.
        5) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_STATUS_CHECKS_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The rule gates a merge on the checks it names, so a rule that names none is enabled but cannot
# block anything. The checkbox is checked, so this is reported as a count rather than as an absent
# rule.
def test_RuleWithoutChecks():
    result = _Evaluate([_NO_CHECKS_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires 0 status check(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# The rule is already enabled, so the resolution names the checks to add rather than directing the
# user to the checkbox.
def test_RuleWithoutChecksResolution():
    result = _Evaluate([_NO_CHECKS_RULE])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Add at least 1 status check(s) beneath the **Require status checks to pass** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_STATUS_CHECKS_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The checks are absent from a rule whose parameters are missing or empty, which is treated the
# same as a rule that names none rather than raising.
@pytest.mark.parametrize("parameters", [{}, {"required_status_checks": None}])
def test_RuleWithoutCheckParameters(parameters):
    result = _Evaluate(
        [{**_REQUIRED_STATUS_CHECKS_RULE, "parameters": parameters}],
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires 0 status check(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# The count is a minimum, so naming fewer checks than requested is an error even though the rule is
# enabled.
def test_FewerChecksThanRequested():
    result = _Evaluate([_REQUIRED_STATUS_CHECKS_RULE], value=2)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires 1 status check(s), but the requirement specifies it must be at least 2."
    )


# ----------------------------------------------------------------------
# The count is a minimum rather than an exact value, so naming more checks than requested satisfies
# the requirement.
def test_MoreChecksThanRequested():
    result = _Evaluate([_TWO_CHECKS_RULE], value=1)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# Checks named by any matching rule count toward the total, since the endpoint reports one rule per
# ruleset that applies to the branch.
def test_ChecksAcrossMultipleRules():
    result = _Evaluate([_NO_CHECKS_RULE, _REQUIRED_STATUS_CHECKS_RULE], value=1)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The resolution names the requested count rather than a fixed one, so it tells the user how many
# checks to add.
def test_ErrorResolutionUsesValue():
    result = _Evaluate([_REQUIRED_STATUS_CHECKS_RULE], value=3)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Add at least 3 status check(s) beneath the **Require status checks to pass** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_STATUS_CHECKS_DOCUMENTATION_URL})
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
# A rule that names no checks is enabled but inert, so it is still reported as present rather than
# as satisfying a count of 0.
@pytest.mark.parametrize(
    "response",
    [[_REQUIRED_STATUS_CHECKS_RULE], [_TWO_CHECKS_RULE], [_NO_CHECKS_RULE]],
)
def test_ZeroWhenRequired(response):
    result = _Evaluate(response, value=0)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires status checks to pass, but the requirement specifies that it must not."
    )


# ----------------------------------------------------------------------
# The resolution clears the checkbox rather than naming checks, since the rule is expected to be
# absent entirely.
def test_ZeroResolution():
    result = _Evaluate([_REQUIRED_STATUS_CHECKS_RULE], value=0)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require status checks to pass** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_STATUS_CHECKS_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The requirement runs by default, so it is only skipped when the user asks for it.
def test_Skipped():
    requirement = RequireStatusChecksToPassRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"skip": True, "value": 1},
    )

    assert result.result == EvaluateResultValue.Skipped
