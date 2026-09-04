import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.suggest_updating_pull_request_branches_requirement import (
    SuggestUpdatingPullRequestBranchesRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-suggestions-to-update-pull-request-branches"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that updating pull request branches is not always
    suggested, which matches the state of a newly created repository. When the setting is
    disabled, the control still appears on branches that a rule requires to be up to date
    before merging; the setting only extends it to every branch that is behind.

    ## Reasons for this Default

    - The update is performed by GitHub rather than the contributor, and GitHub does not sign
      what it produces here. The merge option creates a merge commit authored by the person who
      clicked it, and the rebase option replays the branch's commits as new objects; neither
      receives the web-flow signature that GitHub applies to a merge or squash it performs on
      its own behalf. A project that requires signed commits therefore ends up with a branch it
      can no longer merge, and recovering from it requires rewriting history.
    - The rebase option is the worse of the two, because it strips the signatures from commits
      that were already signed. Every commit on the branch is replayed with a new SHA and the
      signature does not follow it, so a branch that was fully signed becomes fully unsigned.
    - The control is offered where nothing requires it, so contributors update branches that
      did not need updating. Each update rewrites or extends the branch, which restarts status
      checks and invalidates reviews on a pull request that was ready to merge.
    - Where being up to date genuinely matters, a branch protection rule or ruleset should say
      so. The rule surfaces the control on the branches it governs and blocks the merge until
      the branch is current, which is an enforced guarantee rather than a suggestion.

    ## Reasons to Override this Default

    - The project does not require signed commits, and wants contributors to be able to resolve
      a stale branch from the pull request page rather than from the command line.
    - The project relies on the merge option only and accepts unsigned merge commits, since
      that option at least preserves the signatures of the branch's existing commits.

    Note that the setting controls only where the control is offered; it does not require that
    a branch be up to date to merge, which is a branch protection rule or ruleset. Also note
    that a merge queue updates branches itself as part of forming the queue, so a repository
    using one does not need this setting to keep branches current.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SuggestUpdatingPullRequestBranchesRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = SuggestUpdatingPullRequestBranchesRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SuggestUpdatingPullRequestBranchesRequirement()

    assert requirement.name == "SuggestUpdatingPullRequestBranches"
    assert (
        requirement.description
        == "Validates whether the update branch control is offered on every pull request whose branch is behind its base branch; the update it performs produces commits that GitHub does not sign."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SuggestUpdatingPullRequestBranchesRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("allow_update_branch", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(allow_update_branch, require):
    result = _Evaluate({"allow_update_branch": allow_update_branch}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"allow_update_branch": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"allow_update_branch": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"allow_update_branch": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Uncheck the **Always suggest updating pull request branches** checkbox.

        See [Managing suggestions to update pull request branches]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when the suggestion must always be offered.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"allow_update_branch": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Check the **Always suggest updating pull request branches** checkbox.

        See [Managing suggestions to update pull request branches]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"allow_update_branch": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_SuggestionWhenDisallowed():
    result = _Evaluate({"allow_update_branch": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NoSuggestionWhenRequired():
    result = _Evaluate({"allow_update_branch": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An explicit True is a visible setting that is genuinely enabled, so it fails rather than being
# treated as the unknown case.
def test_EnabledIsDistinctFromUnknown():
    result = _Evaluate({"allow_update_branch": True}, pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# GitHub omits the setting for a caller without push access, so an absent key means the value is
# unknown rather than disabled. A missing token is the user's to correct, so it warns.
def test_MissingStatusWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's pull request branch update settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see the setting, which is a
# misconfiguration of the token rather than a repository failure.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's pull request branch update settings are not visible because the Personal Access Token provided does not grant push access to the repository."
    )


# ----------------------------------------------------------------------
# An absent setting cannot be evaluated, so it does not pass merely because the default expects the
# setting to be disabled.
@pytest.mark.parametrize(
    ("pat", "expected_result"),
    [
        (None, EvaluateResultValue.Warning),
        ("my-pat", EvaluateResultValue.Error),
    ],
)
def test_MissingStatusWhenDisallowed(pat, expected_result):
    result = _Evaluate({}, pat=pat)

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
    requirement = SuggestUpdatingPullRequestBranchesRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
