import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_branches_to_be_up_to_date_before_merging import (
    RequireBranchesToBeUpToDateBeforeMergingRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-status-checks-to-pass-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
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


# ----------------------------------------------------------------------
def _CreateStatusChecksRule(
    *,
    strict: bool,
    checks: list[dict] | None = None,
) -> dict:
    return {
        "type": "required_status_checks",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "strict_required_status_checks_policy": strict,
            "do_not_enforce_on_create": False,
            "required_status_checks": (
                [{"context": "build", "integration_id": 15368}] if checks is None else checks
            ),
        },
    }


_OTHER_RULE = {
    "type": "non_fast_forward",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequireBranchesToBeUpToDateBeforeMergingRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    prohibit: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireBranchesToBeUpToDateBeforeMergingRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "prohibit": prohibit},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireBranchesToBeUpToDateBeforeMergingRequirement()

    assert requirement.name == "RequireBranchesToBeUpToDateBeforeMerging"
    assert (
        requirement.description
        == "Validates whether a ruleset requires that a pull request branch is up to date with its base branch before merging, so that status checks run against the merged result."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireBranchesToBeUpToDateBeforeMergingRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "prohibit"),
    [
        ([_CreateStatusChecksRule(strict=True)], False),
        ([_OTHER_RULE, _CreateStatusChecksRule(strict=True)], False),
        ([_CreateStatusChecksRule(strict=False)], True),
    ],
)
def test_MatchingValue(response, prohibit):
    result = _Evaluate(response, prohibit=prohibit)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize(
    "response",
    [[_CreateStatusChecksRule(strict=True)], [_CreateStatusChecksRule(strict=False)]],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The setting determines which commit the required checks run against, so it governs nothing on a
# branch whose ruleset requires no checks. The rationale describes a default that is not being
# applied, so it is omitted along with the resolution.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DoesNotApplyWithoutStatusChecksRule(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require any status checks to pass, so there are no check results that depend on the branch being up to date."
    )
    assert result.resolution is None
    assert result.rationale is None


# ----------------------------------------------------------------------
# GitHub does not apply the setting unless the rule names a check to run, so a rule that is enabled
# while naming none leaves nothing for the setting to govern.
@pytest.mark.parametrize(
    "parameters",
    [
        {"strict_required_status_checks_policy": True, "required_status_checks": []},
        {"strict_required_status_checks_policy": True, "required_status_checks": None},
        {"strict_required_status_checks_policy": True},
        {},
    ],
)
def test_DoesNotApplyWithoutChecks(parameters):
    result = _Evaluate([{**_CreateStatusChecksRule(strict=True), "parameters": parameters}])

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.resolution is None
    assert result.rationale is None


# ----------------------------------------------------------------------
# The status checks rule may be enabled without requiring branches to be up to date, which allows a
# merge whose required checks passed against an older base.
def test_StatusChecksWithoutStrictPolicy():
    result = _Evaluate([_CreateStatusChecksRule(strict=False)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_RequiredWhenProhibited():
    result = _Evaluate([_CreateStatusChecksRule(strict=True)], prohibit=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The setting is reported only when the status checks rule carries it, so a rule whose parameters
# omit it is treated as not requiring freshness rather than as unknown.
def test_MissingParameter():
    rule = _CreateStatusChecksRule(strict=True)
    del rule["parameters"]["strict_required_status_checks_policy"]

    result = _Evaluate([rule])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# The endpoint reports one rule per ruleset that applies to the branch, so the strictest rule is
# the one that governs the merge.
def test_StrictAcrossMultipleRules():
    result = _Evaluate(
        [
            _CreateStatusChecksRule(strict=False),
            _CreateStatusChecksRule(strict=True, checks=[{"context": "test"}]),
        ],
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# A rule that names no checks contributes nothing on its own, but the checks named by another
# matching rule are enough for the setting to apply.
def test_AppliesWhenAnotherRuleNamesChecks():
    result = _Evaluate(
        [
            _CreateStatusChecksRule(strict=False, checks=[]),
            _CreateStatusChecksRule(strict=False),
        ],
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreateStatusChecksRule(strict=False)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require branches to be up to date before merging** checkbox beneath **Require status checks to pass** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the setting when branches must not be required to be up
# to date.
def test_ErrorResolutionWhenProhibited():
    result = _Evaluate([_CreateStatusChecksRule(strict=True)], prohibit=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require branches to be up to date before merging** checkbox beneath **Require status checks to pass** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CreateStatusChecksRule(strict=False)], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        [_CreateStatusChecksRule(strict=False)],
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireBranchesToBeUpToDateBeforeMergingRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "prohibit": False})

    assert result.result == EvaluateResultValue.Skipped
