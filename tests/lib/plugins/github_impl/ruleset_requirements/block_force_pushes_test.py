import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.block_force_pushes import (
    BlockForcePushesRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#block-force-pushes"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset blocks force pushes, which matches
    GitHub's own default when a branch ruleset is created.

    ## Reasons for this Default

    - A force push replaces the branch's history rather than adding to it. Commits that
      others have already fetched and built upon stop being reachable from the branch, so
      every collaborator holding the previous history discovers the change as a conflict
      during their next pull rather than as a reported event.
    - The rewrite is silent and leaves no record on the branch. Because the commits that
      were displaced are no longer referenced, the branch offers no evidence that anything
      was removed, and reconstructing what it previously held depends on a reflog or a local
      clone that has not yet expired.
    - A force push circumvents the review the rest of the ruleset enforces. Requiring a pull
      request, approvals, and passing status checks governs what may be added to the branch,
      but none of them examine a push that discards reviewed commits and substitutes
      unreviewed ones in their place.
    - Rewriting history invalidates work already derived from it. Open pull requests
      targeting the branch report commits that no longer exist, published commit hashes
      stop resolving, and builds or releases that recorded a hash can no longer be
      reproduced from the branch.

    ## Reasons to Override this Default

    - The ruleset targets a pattern covering branches whose history is rewritten as part of
      their normal use, such as topic branches that are rebased before merging or branches
      that tooling regenerates from another source on every run.
    - The repository is a mirror whose branches are overwritten to track an upstream that
      rewrites its own history, where a blocked force push causes the mirror to stop
      reflecting its source.

    Note that this rule blocks force pushes by users with push access rather than by
    everyone. Anyone named in the ruleset's bypass list may still force push, as may a
    repository administrator when the ruleset grants administrators bypass.
    """,
)


# ----------------------------------------------------------------------
_NON_FAST_FORWARD_RULE = {
    "type": "non_fast_forward",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}

_OTHER_RULE = {
    "type": "deletion",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: BlockForcePushesRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    prohibit: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = BlockForcePushesRequirement()

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
    requirement = BlockForcePushesRequirement()

    assert requirement.name == "BlockForcePushes"
    assert (
        requirement.description
        == "Validates whether a ruleset blocks force pushes to the branch, so that its history can only move forward and cannot be rewritten."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = BlockForcePushesRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "prohibit"),
    [
        ([_NON_FAST_FORWARD_RULE], False),
        ([_OTHER_RULE, _NON_FAST_FORWARD_RULE], False),
        ([_OTHER_RULE], True),
        ([], True),
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
@pytest.mark.parametrize("response", [[_NON_FAST_FORWARD_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# non-fast-forward rule is one that accepts force pushes.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_UnblockedWhenRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_BlockedWhenProhibited():
    result = _Evaluate([_NON_FAST_FORWARD_RULE], prohibit=True)

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
        3) Check the **Block force pushes** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the rule when force pushes must not be blocked.
def test_ErrorResolutionWhenProhibited():
    result = _Evaluate([_NON_FAST_FORWARD_RULE], prohibit=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Block force pushes** checkbox in the **Branch rules** section.
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
    requirement = BlockForcePushesRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "prohibit": False})

    assert result.result == EvaluateResultValue.Skipped
