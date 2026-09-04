import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.squash_commit import SquashCommitRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that squash merging is disallowed.

    Note that this differs from the state of a newly created repository, which allows all
    three merge methods.

    ## Reasons for this Default

    - Squashing rewrites the branch's commits into a new commit that no contributor created
      locally, so any signature they carried cannot follow them onto the base branch. The
      replacement is signed with GitHub's web-flow key, which attests that GitHub performed
      the merge rather than that a developer wrote the change.
    - A merge commit is signed with the same web-flow key, but it leaves the branch's signed
      commits reachable as they were authored. Squashing discards them, so the history retains
      no commit signed by the person who wrote the code and the web-flow signature is the only
      one left to verify.
    - Verification of a squashed commit therefore establishes less than it appears to. A reader
      checking signatures finds a valid one on every commit while none of them attests to the
      identity of an author, which is weaker than an unsigned history that does not invite the
      inference.
    - Squashing collapses an entire branch into one revision, so `git bisect` identifies the
      branch rather than the change within it, and `git blame` attributes every line the branch
      touched to a single commit.
    - The commit that lands on the base branch is not the commit that was tested on the branch,
      since it is a new object with a different tree lineage and no parent among the commits
      that status checks ran against.

    ## Reasons to Override this Default

    - The project treats a pull request as one logical change and wants one commit per change
      on the base branch, which is the purpose of the method; this matters most when branches
      accumulate fixup and work-in-progress commits that carry no meaning after review.
    - A branch protection rule or ruleset requires a linear commit history, which merge commits
      cannot satisfy. Squashing produces a linear history without asking contributors to replay
      commits themselves, which rebasing does when GitHub cannot resolve a conflict.
    - The project does not rely on commit signatures for attribution, having established
      authorship through review records or the pull request itself instead.

    Note that a repository must keep at least one merge method enabled, so disallowing this one
    requires that merge commits or rebase merging remain available. Also note that merge queues
    do not honor these settings, since the queue controls the method used for the merges it
    performs, and that restricting a single branch to a particular method is done with a
    ruleset's allowed merge methods rather than here.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SquashCommitRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = SquashCommitRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SquashCommitRequirement()

    assert requirement.name == "SquashCommit"
    assert (
        requirement.description
        == "Validates whether pull requests can be merged by squashing; the method rewrites the branch's commits into one, dropping their authorship and signatures."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SquashCommitRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("allow_squash_merge", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(allow_squash_merge, require):
    result = _Evaluate({"allow_squash_merge": allow_squash_merge}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"allow_squash_merge": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"allow_squash_merge": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"allow_squash_merge": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Uncheck the **Allow squash merging** checkbox.

        See [Configuring commit squashing for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when squash merging must be allowed.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"allow_squash_merge": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Check the **Allow squash merging** checkbox.

        See [Configuring commit squashing for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"allow_squash_merge": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_SquashCommitWhenDisallowed():
    result = _Evaluate({"allow_squash_merge": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NoSquashCommitWhenRequired():
    result = _Evaluate({"allow_squash_merge": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An explicit True is a visible setting that is genuinely enabled, so it fails rather than being
# treated as the unknown case.
def test_EnabledIsDistinctFromUnknown():
    result = _Evaluate({"allow_squash_merge": True}, pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# GitHub omits the squash merge settings for a caller without push access, so an absent key means the
# value is unknown rather than disabled. A missing token is the user's to correct, so it warns.
def test_MissingStatusWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's squash merge settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see the squash merge
# settings, which is a misconfiguration of the token rather than a repository failure.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's squash merge settings are not visible because the Personal Access Token provided does not grant push access to the repository."
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
    requirement = SquashCommitRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
