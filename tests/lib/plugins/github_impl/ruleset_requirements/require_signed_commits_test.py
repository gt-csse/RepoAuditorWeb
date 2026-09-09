import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_signed_commits import (
    RequireSignedCommitsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-signed-commits"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset mandates signed commits.

    Note that this differs from GitHub's own default when a branch ruleset is created, where
    the rule is not selected.

    ## Reasons for this Default

    - The author and committer recorded in a commit are strings the committing tool writes
      at the author's discretion. Nothing in Git checks them, so any contributor can produce
      a commit attributed to anyone else, and the history displays that attribution as
      though it were established. A signature is the only part of a commit that ties it to a
      key rather than to a claim.
    - Attribution on the mainline branch is what the rest of the repository's process is
      recorded against. A review, an approval, and a status check all refer to commits, so
      an unverifiable author undermines the record those controls produce rather than merely
      being cosmetic.
    - The rule is enforced at the point of the push, so the branch cannot accumulate
      unverifiable commits that would have to be rewritten later. Enabling it on a
      repository whose history already contains unsigned commits does not reject those
      commits, because only the commits being introduced are checked.
    - Signing is a one-time configuration for a contributor rather than a per-commit step.
      A key registered with the account and a configured `commit.gpgsign` make every
      subsequent commit signed, and commits authored through GitHub's web interface, along
      with those the merge button creates, are signed by GitHub already.
    - The provenance of a change is not otherwise recoverable after the fact. A repository
      that discovers a commit it did not expect can determine who pushed it from the audit
      log only while that log is retained, whereas a signature remains part of the commit.

    ## Reasons to Override this Default

    - The project accepts contributions from an actor that cannot sign, such as a
      self-hosted runner, a release script, or a bot pushing with a token rather than a
      key, in which case the rule blocks the automation rather than an unverified human.
    - The project's contributors cannot be expected to configure signing, such as a course
      repository or a repository accepting occasional external patches, where the rule
      turns a first contribution into a key-management exercise.
    - The repository mirrors or imports a history produced elsewhere, whose commits were
      signed by keys the repository's contributors do not hold, or were never signed at all.

    Note that the rule interacts with how a pull request is merged. GitHub evaluates
    mergeability against a test merge commit and checks the commits it introduces, so an
    unsigned commit on the head branch blocks a squash merge even though GitHub would sign
    the squash commit it produces. Such a pull request cannot be merged until the head
    branch is rewritten with signed commits or someone with bypass permission merges it.

    Note also that the rule accepts a signature GitHub can verify rather than one made by a
    particular key. A contributor who has enabled vigilant mode has commits marked
    "Partially verified" accepted, and the rule constrains who can be shown to have written
    a commit rather than what the commit contains.
    """,
)


# ----------------------------------------------------------------------
_REQUIRED_SIGNATURES_RULE = {
    "type": "required_signatures",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}

_OTHER_RULE = {
    "type": "non_fast_forward",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequireSignedCommitsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    disallow: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireSignedCommitsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireSignedCommitsRequirement()

    assert requirement.name == "RequireSignedCommits"
    assert (
        requirement.description
        == "Validates whether a ruleset requires that commits pushed to branches matching its pattern carry a signature that GitHub has verified against a known identity."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireSignedCommitsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "disallow"),
    [
        ([_REQUIRED_SIGNATURES_RULE], False),
        ([_OTHER_RULE, _REQUIRED_SIGNATURES_RULE], False),
        ([_OTHER_RULE], True),
        ([], True),
    ],
)
def test_MatchingValue(response, disallow):
    result = _Evaluate(response, disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize("response", [[_REQUIRED_SIGNATURES_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# required signatures rule is one that accepts unsigned commits.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_NotRequiredWhenRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_RequiredWhenDisallowed():
    result = _Evaluate([_REQUIRED_SIGNATURES_RULE], disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require signed commits** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the rule when signed commits must not be required.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate([_REQUIRED_SIGNATURES_RULE], disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require signed commits** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
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
def test_Skip():
    requirement = RequireSignedCommitsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
