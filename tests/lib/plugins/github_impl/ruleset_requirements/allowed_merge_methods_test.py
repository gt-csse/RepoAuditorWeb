import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.allowed_merge_methods import (
    AllowedMergeMethodsRequirement,
    Values,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset allows the merge commit method alone.

    Note that this differs from GitHub's own default when the pull request rule is added to
    a branch ruleset, where all three methods are allowed.

    ## Reasons for this Default

    - The merge commit is the only method that lands the commits that were reviewed and
      tested. Squashing rewrites a branch into a new commit and rebasing replays each commit
      onto a base that has moved, so in both cases the object that reaches the branch is not
      the object the status checks ran against.
    - It is the only method that preserves a contributor's signatures. A squash discards the
      authored commits in favor of one signed with GitHub's web-flow key, and a rebase lands
      commits that nothing signs at all, so neither history retains a signature attesting to
      who wrote the code.
    - Restricting the branch to one method is what makes its history uniform. Leaving the
      choice to whoever clicks merge produces a branch whose shape depends on who landed
      each change, so tooling that reads the history has to accommodate every method the
      ruleset permits.
    - The ruleset is where the restriction holds for the branch that matters. The
      repository's own merge method checkboxes apply to every branch at once, so a project
      that wants a strict default branch alongside a permissive release or integration
      branch can express that only here.
    - Narrowing the methods costs a contributor nothing. The pull request is merged the same
      way regardless of which methods are permitted; the rule removes options from the merge
      button rather than adding a step to the process.

    ## Reasons to Override this Default

    - The project treats a pull request as one logical change and wants a single commit per
      change on the branch, which is what squashing produces; this matters most where
      branches accumulate fixup and work-in-progress commits that carry no meaning once the
      review is over.
    - The ruleset also requires a linear history, which no merge commit can satisfy. Such a
      ruleset must allow squashing, rebasing, or both, and allowing the merge commit alone
      leaves a merge button that the linear history rule rejects.
    - The project curates its branches so that each commit is a meaningful, independently
      reviewable step, and regards collapsing them into one as the greater loss (`rebase`).
    - Contributors need the choice because the right method depends on the change, such as a
      repository that squashes routine work but merges a long-running branch whose commits
      are worth keeping.

    Note that a ruleset can only narrow what the repository already allows, so a method
    selected here is still unavailable unless the corresponding **Pull Requests** checkbox
    in the repository's settings is also enabled. A ruleset that names a method the
    repository disallows blocks the merge rather than enabling the method.

    Note also that merge queues do not honor this setting, since the queue controls the
    method used for the merges it performs.

    Note also that actors granted bypass permission on the ruleset may merge using a method
    it excludes, so the setting describes the path that contributors take rather than one
    that cannot be circumvented.
    """,
)


# ----------------------------------------------------------------------
def _CreatePullRequestRule(allowed_merge_methods: list[str]) -> dict:
    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews_on_push": True,
            "require_code_owner_review": False,
            "require_last_push_approval": False,
            "required_review_thread_resolution": True,
            "allowed_merge_methods": allowed_merge_methods,
        },
    }


_OTHER_RULE = {
    "type": "non_fast_forward",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: AllowedMergeMethodsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    value: list[Values] | None = None,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = AllowedMergeMethodsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "value": [Values.Merge] if value is None else value},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = AllowedMergeMethodsRequirement()

    assert requirement.name == "AllowedMergeMethods"
    assert (
        requirement.description
        == "Validates which merge methods a ruleset permits when a pull request targeting branches matching its pattern is merged."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = AllowedMergeMethodsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type == list[Values]
    assert parameters["value"].default == [Values.Merge]


# ----------------------------------------------------------------------
def test_MatchingValue():
    result = _Evaluate([_CreatePullRequestRule(["merge"])])

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
def test_MatchingValueWithOtherRules():
    result = _Evaluate([_OTHER_RULE, _CreatePullRequestRule(["merge"])])

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize(
    "response",
    [[_CreatePullRequestRule(["merge"])], [_CreatePullRequestRule(["merge", "squash", "rebase"])]],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The methods are a setting of the pull request rule, so they govern nothing on a branch whose
# ruleset does not require a pull request. The rationale describes a default that is not being
# applied, so it is omitted along with the resolution.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DoesNotApplyWithoutPullRequestRule(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so no merge method is imposed on the branch."
    )
    assert result.resolution is None
    assert result.rationale is None


# ----------------------------------------------------------------------
# GitHub's own default allows all three methods, which leaves the choice of method to whoever
# clicks the merge button.
def test_AllMethodsAllowed():
    result = _Evaluate([_CreatePullRequestRule(["merge", "squash", "rebase"])])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'Merge, Squash, Rebase', but the requirement specifies it must be 'Merge'."
    )


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("allowed_merge_methods", "expected"),
    [
        (["squash"], "Squash"),
        (["rebase"], "Rebase"),
        (["squash", "rebase"], "Squash, Rebase"),
        (["merge", "squash"], "Merge, Squash"),
    ],
)
def test_WrongMethods(allowed_merge_methods, expected):
    result = _Evaluate([_CreatePullRequestRule(allowed_merge_methods)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        f"The repository's value is '{expected}', but the requirement specifies it must be 'Merge'."
    )


# ----------------------------------------------------------------------
# The value parameter is repeatable, so a project that permits more than one method names each of
# them rather than choosing a single one.
@pytest.mark.parametrize(
    ("allowed_merge_methods", "value"),
    [
        (["squash"], [Values.Squash]),
        (["squash", "rebase"], [Values.Squash, Values.Rebase]),
        (["merge", "squash", "rebase"], [Values.Merge, Values.Squash, Values.Rebase]),
    ],
)
def test_ValueOverridesDefault(allowed_merge_methods, value):
    result = _Evaluate([_CreatePullRequestRule(allowed_merge_methods)], value=value)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The checkboxes are a set, so the order the methods are reported in carries no meaning and a
# ruleset that lists them differently than they were requested still matches.
def test_OrderIsInsignificant():
    result = _Evaluate(
        [_CreatePullRequestRule(["rebase", "merge", "squash"])],
        value=[Values.Squash, Values.Merge, Values.Rebase],
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# A method named twice on the command line describes the same set as naming it once.
def test_DuplicateValuesAreEquivalent():
    result = _Evaluate(
        [_CreatePullRequestRule(["squash"])],
        value=[Values.Squash, Values.Squash],
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The setting is reported only when the pull request rule carries it, so a rule whose parameters
# omit it is treated as restricting the branch to no particular method.
@pytest.mark.parametrize(
    "parameters",
    [{"allowed_merge_methods": []}, {"allowed_merge_methods": None}, {}],
)
def test_MissingParameter(parameters):
    result = _Evaluate([{**_CreatePullRequestRule(["merge"]), "parameters": parameters}])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is '<none>', but the requirement specifies it must be 'Merge'."
    )


# ----------------------------------------------------------------------
# The endpoint reports one rule per ruleset that applies to the branch, so the first pull request
# rule is the one that is evaluated.
def test_MultiplePullRequestRules():
    result = _Evaluate(
        [_CreatePullRequestRule(["merge"]), _CreatePullRequestRule(["squash"])],
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(["squash"])])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check **Merge** beneath **Require a pull request before merging** in the **Branch rules** section, clearing the methods that are not listed.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution names each method that the requirement expects, so a user allowing more than one
# is not asked to clear the others.
def test_ErrorResolutionNamesEachExpectedMethod():
    result = _Evaluate(
        [_CreatePullRequestRule(["merge"])],
        value=[Values.Squash, Values.Rebase],
    )

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check **Squash**, **Rebase** beneath **Require a pull request before merging** in the **Branch rules** section, clearing the methods that are not listed.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CreatePullRequestRule(["squash"])], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        [_CreatePullRequestRule(["squash"])],
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = AllowedMergeMethodsRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"skip": True, "value": [Values.Merge]},
    )

    assert result.result == EvaluateResultValue.Skipped
