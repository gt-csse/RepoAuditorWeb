import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.rebase_commit import RebaseCommitRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-rebasing-for-pull-requests"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that rebase merging is disallowed.

    Note that this differs from the state of a newly created repository, which allows all
    three merge methods.

    ## Reasons for this Default

    - Rebasing replays each of the branch's commits onto the base branch as a new commit with
      updated committer information and a new SHA, so any signature the original carried does
      not follow it. The result is a history of unsigned commits.
    - GitHub cannot sign the replacements either. It does not hold the committer's signing key
      and the commits are not its own to attest to, so unlike a merge commit or a squash
      commit there is no web-flow signature to substitute. Requiring signed commits on the
      base branch therefore blocks the method outright, with GitHub reporting that rebase
      merges cannot be automatically signed.
    - This makes the method the worst of the three for attribution. A merge commit preserves
      the branch's signed commits as authored, and a squash commit at least lands one signed
      object; rebasing lands several commits, none of which is signed by anyone.
    - The commits that land are not the commits that were tested, since each is a new object
      with a different parent from the one status checks ran against, and the branch's
      intermediate states are replayed onto a base that has moved since.
    - The method also drops commits that were empty to begin with, so the history that lands
      is not the history that was reviewed.

    ## Reasons to Override this Default

    - A branch protection rule or ruleset requires a linear commit history and the project
      wants the branch's individual commits on the base branch rather than one squashed
      commit, which is what distinguishes this method from squash merging.
    - The project curates its branches so that each commit is a meaningful, independently
      reviewable step, and treats losing those boundaries to a squash as the greater cost.
    - The project does not rely on commit signatures for attribution, having established
      authorship through review records or the pull request itself instead.

    Note that a repository must keep at least one merge method enabled, so disallowing this one
    requires that merge commits or squash merging remain available. Also note that merge queues
    do not honor these settings, since the queue controls the method used for the merges it
    performs, and that restricting a single branch to a particular method is done with a
    ruleset's allowed merge methods rather than here. GitHub refuses to rebase when it cannot
    do so safely, in which case the work of replaying the commits falls to the branch's author.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: RebaseCommitRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = RebaseCommitRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RebaseCommitRequirement()

    assert requirement.name == "RebaseCommit"
    assert (
        requirement.description
        == "Validates whether pull requests can be merged by rebasing; the method replays commits onto the base branch as new commits, dropping their signatures."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RebaseCommitRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("allow_rebase_merge", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(allow_rebase_merge, require):
    result = _Evaluate({"allow_rebase_merge": allow_rebase_merge}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"allow_rebase_merge": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"allow_rebase_merge": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"allow_rebase_merge": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Uncheck the **Allow rebase merging** checkbox.

        See [Configuring commit rebasing for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when rebase merging must be allowed.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"allow_rebase_merge": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Check the **Allow rebase merging** checkbox.

        See [Configuring commit rebasing for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"allow_rebase_merge": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_RebaseCommitWhenDisallowed():
    result = _Evaluate({"allow_rebase_merge": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NoRebaseCommitWhenRequired():
    result = _Evaluate({"allow_rebase_merge": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An explicit True is a visible setting that is genuinely enabled, so it fails rather than being
# treated as the unknown case.
def test_EnabledIsDistinctFromUnknown():
    result = _Evaluate({"allow_rebase_merge": True}, pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# GitHub omits the rebase merge settings for a caller without push access, so an absent key means the
# value is unknown rather than disabled. A missing token is the user's to correct, so it warns.
def test_MissingStatusWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's rebase merge settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see the rebase merge
# settings, which is a misconfiguration of the token rather than a repository failure.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's rebase merge settings are not visible because the Personal Access Token provided does not grant push access to the repository."
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
    requirement = RebaseCommitRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
