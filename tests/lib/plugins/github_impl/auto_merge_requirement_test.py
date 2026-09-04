import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.auto_merge_requirement import AutoMergeRequirement
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that auto-merge is enabled.

    Note that this differs from the state of a newly created repository, where the setting is
    disabled.

    ## Reasons for this Default

    - The setting relaxes nothing. Auto-merge merges only once every required review and
      status check has passed, which are the same conditions that gate the merge button, so
      a pull request that auto-merge lands is one that a person could have landed by hand at
      that moment. The branch protection rules and rulesets remain the authority over what
      may merge.
    - Without it, a pull request that has satisfied every requirement waits on someone
      noticing that it has. That delay is not a review of anything, since the review already
      happened, and the branch grows staler while it lasts.
    - Enabling it removes the incentive to sit on the merge button while checks run. Someone
      watching a long test suite so they can merge at the end is the case the setting exists
      to replace, and the alternative to it is a person merging from memory rather than from
      a signal.
    - The control is offered only on pull requests that cannot merge immediately, so it
      cannot be used to bypass a wait that does not exist, and only users with write access
      can enable it on a pull request.
    - Auto-merge disables itself when someone without write access pushes to the head branch
      or the base branch is changed, so a queued merge does not carry over to work that
      arrived after it was queued.
    - The setting only makes the control available. Each pull request still has to have
      auto-merge turned on individually, so enabling it here does not cause anything to merge
      on its own.

    ## Reasons to Override this Default

    - The project's merge requirements do not fully describe when a merge is acceptable, and
      a person is expected to apply judgment that no status check encodes. Auto-merge is only
      as trustworthy as the rules it waits on, so a repository whose rules are advisory
      should not offer it.
    - Merges are deliberately coordinated with something outside the repository, such as a
      release window or a deployment that a merge triggers, where landing a change as soon as
      it is ready is the wrong outcome.
    - The project requires signed commits and relies on the merge and squash methods, whose
      commits GitHub signs with its own web-flow key rather than the merging user's; a
      project that wants merges attributed to a human signature would rather they be
      performed by hand.

    Note that a repository using a merge queue does not need this setting, since the queue
    performs the merges itself once a pull request is added to it.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: AutoMergeRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = AutoMergeRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = AutoMergeRequirement()

    assert requirement.name == "AutoMerge"
    assert (
        requirement.description
        == "Validates whether a pull request can be queued to merge once its requirements are met; the same reviews and status checks still apply."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = AutoMergeRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("allow_auto_merge", "disallow"),
    [(True, False), (False, True)],
)
def test_MatchingStatus(allow_auto_merge, disallow):
    result = _Evaluate({"allow_auto_merge": allow_auto_merge}, disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"allow_auto_merge": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"allow_auto_merge": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"allow_auto_merge": False})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Check the **Allow auto-merge** checkbox.

        See [Managing auto-merge for pull requests in your repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to uncheck the setting when auto-merge must be disabled.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate({"allow_auto_merge": True}, disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Uncheck the **Allow auto-merge** checkbox.

        See [Managing auto-merge for pull requests in your repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"allow_auto_merge": False}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_NoAutoMergeWhenRequired():
    result = _Evaluate({"allow_auto_merge": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_AutoMergeWhenDisallowed():
    result = _Evaluate({"allow_auto_merge": True}, disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An explicit False is a visible setting that is genuinely disabled, so it fails rather than being
# treated as the unknown case.
def test_DisabledIsDistinctFromUnknown():
    result = _Evaluate({"allow_auto_merge": False}, pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# GitHub omits the auto-merge setting for a caller without push access, so an absent key means the
# value is unknown rather than disabled. A missing token is the user's to correct, so it warns.
def test_MissingStatusWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's auto-merge settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see the auto-merge setting,
# which is a misconfiguration of the token rather than a repository failure.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's auto-merge settings are not visible because the Personal Access Token provided does not grant push access to the repository."
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
    requirement = AutoMergeRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
