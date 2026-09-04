import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.delete_branch_on_merge import (
    DeleteBranchOnMergeRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that head branches are automatically deleted when
    pull requests are merged.

    Note that this differs from the state of a newly created repository, where the setting is
    disabled.

    ## Reasons for this Default

    - Short-lived branches are preferable to long-lived ones. A branch that disappears when
      its work lands cannot accumulate a second change, drift behind the base branch, or
      become a place where work waits; deleting it on merge is what makes the short lifetime
      the default outcome rather than something each contributor has to remember.
    - A merged branch describes no work that is not already on the base branch, so what
      remains is a name that outlives its meaning. The branch list is a list of work in
      progress only if the entries that are no longer in progress leave it.
    - Deleting the branch by hand is a step after the merge, performed by whoever notices,
      so the branches that survive are the ones nobody attended to rather than the ones that
      were meant to. Automating it removes the judgment from a decision that has only one
      correct answer.
    - Nothing is lost. The branch is restorable from the pull request that merged it, and
      the commits are reachable from the base branch, so the ref is a convenience rather
      than the record of the work.
    - Deletion is skipped for a branch that another open pull request still references, and
      open pull requests that targeted the deleted branch are retargeted to the merged pull
      request's base branch rather than closed, so the setting does not strand work in
      review.
    - Branch protection rules and rulesets take precedence, so a branch that a rule protects
      from deletion is not deleted regardless of this setting.

    ## Reasons to Override this Default

    - Branch names carry meaning beyond the merge, such as a release or integration branch
      that is merged repeatedly and expected to persist. Rules should protect such branches,
      but a project that has not written those rules may prefer not to rely on them.
    - Something outside the repository reads the head branch after the merge, such as a
      deployment, an external tracker, or a CI job that resolves the branch name rather than
      the commit.

    Note that the setting governs head branches in this repository only; a pull request from
    a fork has its head branch in the fork, which this repository's setting does not control.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: DeleteBranchOnMergeRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = DeleteBranchOnMergeRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = DeleteBranchOnMergeRequirement()

    assert requirement.name == "DeleteBranchOnMerge"
    assert (
        requirement.description
        == "Validates whether a pull request's head branch is deleted once it merges; the branch remains restorable from the pull request afterwards."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = DeleteBranchOnMergeRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("delete_branch_on_merge", "disallow"),
    [(True, False), (False, True)],
)
def test_MatchingStatus(delete_branch_on_merge, disallow):
    result = _Evaluate({"delete_branch_on_merge": delete_branch_on_merge}, disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"delete_branch_on_merge": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"delete_branch_on_merge": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"delete_branch_on_merge": False})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Check the **Automatically delete head branches** checkbox.

        See [Managing the automatic deletion of branches]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to uncheck the setting when branch deletion must be disabled.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate({"delete_branch_on_merge": True}, disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Uncheck the **Automatically delete head branches** checkbox.

        See [Managing the automatic deletion of branches]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        {"delete_branch_on_merge": False},
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_NoDeleteBranchOnMergeWhenRequired():
    result = _Evaluate({"delete_branch_on_merge": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_DeleteBranchOnMergeWhenDisallowed():
    result = _Evaluate({"delete_branch_on_merge": True}, disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An explicit False is a visible setting that is genuinely disabled, so it fails rather than being
# treated as the unknown case.
def test_DisabledIsDistinctFromUnknown():
    result = _Evaluate({"delete_branch_on_merge": False}, pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# GitHub omits the branch deletion setting for a caller without push access, so an absent key means
# the value is unknown rather than disabled. A missing token is the user's to correct, so it warns.
def test_MissingStatusWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's branch deletion settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see the branch deletion
# setting, which is a misconfiguration of the token rather than a repository failure.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's branch deletion settings are not visible because the Personal Access Token provided does not grant push access to the repository."
    )


# ----------------------------------------------------------------------
# The setting cannot be evaluated when it is not visible, so 'disallow' does not turn an unknown
# value into a passing result.
@pytest.mark.parametrize(
    ("pat", "expected_result"),
    [
        (None, EvaluateResultValue.Warning),
        ("my-pat", EvaluateResultValue.Error),
    ],
)
def test_MissingStatusWhenDisallowed(pat, expected_result):
    result = _Evaluate({}, disallow=True, pat=pat)

    assert result.result == expected_result


# ----------------------------------------------------------------------
# The rationale explains a default that could not be evaluated, so it is omitted when the setting is
# not visible; the problem is the token rather than the repository's configuration.
@pytest.mark.parametrize("pat", [None, "my-pat"])
def test_MissingStatusHasNoRationale(pat):
    result = _Evaluate({}, pat=pat)

    assert result.rationale is None


# ----------------------------------------------------------------------
def test_Skip():
    requirement = DeleteBranchOnMergeRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
