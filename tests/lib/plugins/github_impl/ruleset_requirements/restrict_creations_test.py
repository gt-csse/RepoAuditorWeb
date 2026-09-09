import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_creations import (
    RestrictCreationsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#restrict-creations"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset does not restrict creations, which
    matches GitHub's own default when a branch ruleset is created.

    ## Reasons for this Default

    - The rule governs bringing a name into existence, not what may be pushed to it. A branch
      that already exists is unaffected by it, so on a ruleset targeting an established
      branch the rule protects nothing that the deletion and force-push rules do not already
      protect.
    - A ruleset targeting a pattern rather than a single name commonly covers branches that
      contributors are expected to create, such as `release/*` or `feature/*`. Restricting
      creation there blocks the ordinary act of starting work, and the failure surfaces as a
      rejected push rather than as an explanation of the policy.
    - Creating a branch is reversible and reachable only through the rules that govern
      merging it back. The cost of a wrongly created branch is a stale name; the cost of a
      wrongly blocked creation is contributors unable to begin.
    - Automation that opens pull requests, such as dependency update bots and release
      tooling, creates branches as its first step. Each such actor has to be added to the
      bypass list before the rule takes effect, and one that is missed fails silently until
      someone investigates.

    ## Reasons to Override this Default

    - The ruleset targets a namespace whose names carry meaning that consumers rely on, such
      as `v*` release branches or a `production` deployment branch, where an unsanctioned
      name is itself the problem rather than its contents.
    - The repository is a mirror or a published artifact whose branch set is generated
      rather than authored, where any branch that a person creates is unintended.

    Note that this rule restricts who may create a matching branch rather than preventing
    creation outright. Anyone named in the ruleset's bypass list may still create one, as may
    a repository administrator when the ruleset grants administrators bypass.
    """,
)


# ----------------------------------------------------------------------
_CREATION_RULE = {
    "type": "creation",
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
def _CreateModule(requirement: RestrictCreationsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    require: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RestrictCreationsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RestrictCreationsRequirement()

    assert requirement.name == "RestrictCreations"
    assert (
        requirement.description
        == "Validates whether a ruleset restricts creation of branches matching its pattern, so that only those with bypass permissions can create them."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RestrictCreationsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "require"),
    [
        ([], False),
        ([_OTHER_RULE], False),
        ([_CREATION_RULE], True),
        ([_OTHER_RULE, _CREATION_RULE], True),
    ],
)
def test_MatchingValue(response, require):
    result = _Evaluate(response, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize("response", [[_CREATION_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_RestrictedWhenNotRequired():
    result = _Evaluate([_CREATION_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# creation rule is one whose creation is unrestricted.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_UnrestrictedWhenRequired(response):
    result = _Evaluate(response, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CREATION_RULE])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Restrict creations** checkbox in the **Rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to set the rule when creations must be restricted.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate([], require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Restrict creations** checkbox in the **Rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CREATION_RULE], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate([_CREATION_RULE], url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RestrictCreationsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
