import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_linear_history import (
    RequireLinearHistoryRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-linear-history"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset does not require a linear history,
    which matches GitHub's own default when a branch ruleset is created.

    ## Reasons for this Default

    - The rule forbids merge commits, so it leaves squash merging and rebase merging as the
      only ways a pull request can land. Both rewrite the branch's commits into new objects,
      and the signatures those commits carried do not follow them, so the rule buys a linear
      history at the cost of every contributor signature on the base branch.
    - These requirements default to allowing merge commits and disallowing both squash
      merging and rebase merging, which makes the merge commit the only method a pull request
      may use. Requiring a linear history alongside that configuration leaves a pull request
      with no permitted merge method at all.
    - The rule discards the record of the integration. A merge commit names both the base
      branch and the merged branch as parents, which is what allows `git log --first-parent`
      to read as a list of integrations; a linear history has no such record and cannot
      distinguish a merged branch from a sequence of direct commits.
    - Unlike the branch protection rule of the same name, the ruleset evaluates the history
      that is already present rather than only the commits being pushed. Enabling it on a
      repository whose branch already contains merge commits rejects every subsequent push,
      which cannot be resolved without rewriting the history.
    - Linearity is a property of how the history reads rather than of what it admits. The
      rules that determine whether a change is fit to land, such as requiring a pull request,
      requiring status checks, and requiring signatures, are unaffected by whether the
      commits sit in a line.

    ## Reasons to Override this Default

    - The project treats a pull request as one logical change and has standardized on squash
      merging, in which case the history is already linear and the rule enforces on the
      branch what the repository's merge settings express as a preference.
    - The project relies on tooling that assumes a total order of commits, such as bisecting
      scripts, release automation that derives a changelog by walking commits, or a
      deployment process that identifies a revision by its position in the history.
    - The repository is new or its history was rewritten deliberately, so no merge commit is
      present to trip the evaluation of the existing history.

    Note that the rule cannot be satisfied unless the repository allows squash merging or
    rebase merging, so enabling it while merge commits are the only permitted method
    presents contributors with a merge button that the rule refuses.
    """,
)


# ----------------------------------------------------------------------
_LINEAR_HISTORY_RULE = {
    "type": "required_linear_history",
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
def _CreateModule(requirement: RequireLinearHistoryRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    require: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireLinearHistoryRequirement()

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
    requirement = RequireLinearHistoryRequirement()

    assert requirement.name == "RequireLinearHistory"
    assert (
        requirement.description
        == "Validates whether a ruleset requires a linear history for branches matching its pattern, which prevents merge commits and forces squash or rebase merges."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireLinearHistoryRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "require"),
    [
        ([], False),
        ([_OTHER_RULE], False),
        ([_LINEAR_HISTORY_RULE], True),
        ([_OTHER_RULE, _LINEAR_HISTORY_RULE], True),
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
@pytest.mark.parametrize("response", [[_LINEAR_HISTORY_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_LinearWhenNotRequired():
    result = _Evaluate([_LINEAR_HISTORY_RULE])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the
# linear history rule is one that still accepts merge commits.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_NotLinearWhenRequired(response):
    result = _Evaluate(response, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_LINEAR_HISTORY_RULE])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require linear history** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to set the rule when a linear history must be required.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate([], require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require linear history** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_LINEAR_HISTORY_RULE], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate([_LINEAR_HISTORY_RULE], url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireLinearHistoryRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
