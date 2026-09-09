import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_deletions import (
    RestrictDeletionsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#restrict-deletions"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset restricts deletions, which matches
    GitHub's own default when a branch ruleset is created.

    ## Reasons for this Default

    - Deleting a branch removes the only name that keeps its commits reachable. Nothing
      rejects the deletion and nothing records what the name pointed at, so recovering the
      branch requires someone to still hold the commit hash in a local clone or a reflog
      that has not yet expired.
    - A deletion defeats the protections attached to the branch rather than violating them.
      Required reviews, status checks, and a blocked force push all constrain what may be
      pushed to a branch that exists; none of them apply once the branch is gone.
    - The branch this query targets is the one consumers reference by name. Its deletion
      breaks clones, pull requests opened against it, workflows triggered on it, and
      published links to it, so the cost is borne by everyone reading the repository rather
      than by the person who deleted it.
    - A deletion is a single unconfirmed API call or a click in the branches list, and the
      deleting actor needs only push access. Restricting it converts an irreversible action
      into one that requires bypass permissions.

    ## Reasons to Override this Default

    - The ruleset targets a pattern that intentionally covers transient branches, such as
      release or integration branches that tooling creates and deletes as part of its normal
      operation, where a blocked deletion presents as an unexplained automation failure.
    - The repository is a fork, mirror, or scratch repository whose branches are recreated
      from an upstream source, where the branch carries no history that its upstream does
      not already hold.

    Note that this rule restricts who may delete the branch rather than preventing deletion
    outright. Anyone named in the ruleset's bypass list may still delete it, as may a
    repository administrator when the ruleset grants administrators bypass.
    """,
)


# ----------------------------------------------------------------------
_DELETION_RULE = {
    "type": "deletion",
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
def _CreateModule(requirement: RestrictDeletionsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    prohibit: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RestrictDeletionsRequirement()

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
    requirement = RestrictDeletionsRequirement()

    assert requirement.name == "RestrictDeletions"
    assert (
        requirement.description
        == "Validates whether a ruleset restricts deletion of the branch, so that only those with bypass permissions can delete it."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RestrictDeletionsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "prohibit"),
    [
        ([_DELETION_RULE], False),
        ([_OTHER_RULE, _DELETION_RULE], False),
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
@pytest.mark.parametrize("response", [[_DELETION_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# deletion rule is one whose deletion is unrestricted.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_UnrestrictedWhenRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_RestrictedWhenProhibited():
    result = _Evaluate([_DELETION_RULE], prohibit=True)

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
        3) Check the **Restrict deletions** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the rule when deletions must not be restricted.
def test_ErrorResolutionWhenProhibited():
    result = _Evaluate([_DELETION_RULE], prohibit=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Restrict deletions** checkbox in the **Branch rules** section.
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
    requirement = RestrictDeletionsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "prohibit": False})

    assert result.result == EvaluateResultValue.Skipped
