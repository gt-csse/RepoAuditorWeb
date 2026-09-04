import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.merge_commit_requirement import MergeCommitRequirement
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that merge commits are allowed, which matches the state
    of a newly created repository.

    ## Reasons for this Default

    - The merge commit is the only merge method that leaves the branch's commits reachable as
      they were authored. Squashing and rebasing both rewrite them, so the commit that was
      tested on the branch is not the commit that lands on the base branch.
    - The method records the integration itself. A merge commit has both the base branch and
      the merged branch as parents, so `git log --first-parent` reads as a list of integrations
      while the full history retains the work that each one brought in.
    - Preserving the authored commits keeps `git bisect` and `git blame` pointed at the change
      that actually introduced a behavior, rather than at a squashed commit that collapses an
      entire branch into one revision.
    - The method requires nothing of the contributor. Rebasing is refused when it would produce
      a conflict that GitHub cannot resolve, which pushes the work of replaying commits back
      onto the branch's author; a merge commit can represent that resolution instead.
    - Disabling every merge method leaves pull requests with no merge button at all, so the
      repository has to keep at least one enabled and this is the method that discards the
      least information.

    ## Reasons to Override this Default

    - A branch protection rule or ruleset requires a linear commit history, which merge commits
      cannot satisfy. Such a repository must allow squash merging, rebase merging, or both, and
      leaving this method enabled offers contributors a merge button that the rule will reject.
    - The project treats a pull request as a single logical change and wants one commit per
      change on the base branch, in which case squash merging produces the intended history and
      this method would let a branch's intermediate commits through.
    - The project regards merge commits as noise in the history it publishes, since `--no-ff`
      means one is created even where the branch could have fast-forwarded.
    - Enabling exactly one merge method is how a repository enforces that method, so a project
      that has standardized on squashing or rebasing disables this one to remove the choice.

    Note that merge queues do not honor these settings, since the queue controls the method
    used for the merges it performs. Also note that this setting governs the whole repository,
    so restricting a single branch to a particular method is done with a ruleset's allowed
    merge methods rather than here; a ruleset can only narrow what the repository allows, so
    this setting has to remain enabled for a ruleset to permit it anywhere.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: MergeCommitRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = MergeCommitRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = MergeCommitRequirement()

    assert requirement.name == "MergeCommit"
    assert (
        requirement.description
        == "Validates whether pull requests can be merged with a merge commit; the method merges with `--no-ff`, so the branch's individual commits are preserved under a commit that records the integration."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = MergeCommitRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("allow_merge_commit", "disallow"),
    [(True, False), (False, True)],
)
def test_MatchingStatus(allow_merge_commit, disallow):
    result = _Evaluate({"allow_merge_commit": allow_merge_commit}, disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"allow_merge_commit": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"allow_merge_commit": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"allow_merge_commit": False})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Check the **Allow merge commits** checkbox.

        See [Configuring commit merging for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to uncheck the setting when merge commits must be disallowed.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate({"allow_merge_commit": True}, disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Uncheck the **Allow merge commits** checkbox.

        See [Configuring commit merging for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"allow_merge_commit": False}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_NoMergeCommitWhenRequired():
    result = _Evaluate({"allow_merge_commit": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_MergeCommitWhenDisallowed():
    result = _Evaluate({"allow_merge_commit": True}, disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An explicit False is a visible setting that is genuinely disabled, so it fails rather than being
# treated as the unknown case.
def test_DisabledIsDistinctFromUnknown():
    result = _Evaluate({"allow_merge_commit": False}, pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# GitHub omits the merge settings for a caller without push access, so an absent key means the value
# is unknown rather than disabled. A missing token is the user's to correct, so it warns.
def test_MissingStatusWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's merge settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see the merge settings,
# which is a misconfiguration of the token rather than a repository failure.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's merge settings are not visible because the Personal Access Token provided does not grant push access to the repository."
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
    requirement = MergeCommitRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
