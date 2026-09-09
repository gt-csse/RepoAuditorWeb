import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_approval_of_most_recent_push import (
    RequireApprovalOfMostRecentPushRequirement,
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
    The default behavior is to require that a ruleset does not require approval of the most
    recent reviewable push, which matches GitHub's own default when a branch ruleset is
    created.

    ## Reasons for this Default

    - The rule presumes there is somebody other than the author available to approve. GitHub
      does not accept an approval from the person who made the most recent push, so on a
      repository maintained by one person, or by a group whose members are not consistently
      available, the pull request is blocked until somebody bypasses the ruleset.
    - It acts on every push rather than on pushes that change what would merge. A commit
      that only adjusts a comment, or a click of **Update branch** that brings in unrelated
      work, invalidates the last approval on the same terms as a substantive rewrite, so the
      cost is paid on changes where there is nothing new to review.
    - The risk it addresses is more precisely handled by **Dismiss stale pull request
      approvals when new commits are pushed**, which is driven by the diff changing rather
      than by authorship of the latest push, and which is the setting a project is more
      likely to want if it adopts only one of the two.
    - Requiring approvals already establishes that somebody other than the author agreed to
      the change, because GitHub does not count an author's approval toward the required
      count. This rule narrows that to the most recent push specifically, which is a
      stricter guarantee than many projects need.
    - Where it blocks a merge that the team considers ready, the available remedy is bypass
      permission. Routine merges performed as bypasses convert the bypass list from an
      exception path into the normal one, which weakens every other rule in the ruleset
      alongside this one.

    ## Reasons to Override this Default

    - Without the setting, the last change to a pull request can be made by its author and
      merged on the strength of approvals granted before that change existed. Enabling it
      establishes that whatever lands was seen by a second person in the state it lands in.
    - It closes the gap that a hurried author or a bad actor would use. A pull request can be
      opened small, approved, and then extended with a further commit, and the approval
      requirement ends up satisfied by code that nobody agreed to.
    - It preserves review effort in a way that dismissing stale approvals does not. Existing
      approvals are kept rather than discarded, so only the latest push needs a fresh look,
      which GitHub describes as a compromise for complex pull requests that would otherwise
      have every review dismissed.
    - The person who reviews last is positioned to check what matters most: that earlier
      feedback was applied, and that no unreviewed content was added alongside it.
    - The team is large enough that a second approver is reliably available, and somebody who
      has already reviewed the pull request may re-approve to satisfy the requirement, so the
      rule does not force a new reviewer to be found.

    Note that this setting and **Dismiss stale pull request approvals when new commits are
    pushed** address the same risk by different means and may be used together or
    separately. Dismissal discards approvals whenever a push changes the diff, while this
    setting keeps them and requires only that the most recent push carry an approval from
    somebody else.

    Note also that enabling this setting causes GitHub to reject a merge commit that is
    created manually and pushed directly to the branch, unless the contents of the merge
    exactly match the merge it would have generated for the pull request.

    Note also that actors granted bypass permission on the ruleset may merge without
    satisfying the approval requirement at all, so the setting describes the path that
    contributors take rather than one that cannot be circumvented.
    """,
)


# ----------------------------------------------------------------------
def _CreatePullRequestRule(*, require_last_push_approval: bool) -> dict:
    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False,
            "require_last_push_approval": require_last_push_approval,
            "required_review_thread_resolution": False,
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
def _CreateModule(requirement: RequireApprovalOfMostRecentPushRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    require: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireApprovalOfMostRecentPushRequirement()

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
    requirement = RequireApprovalOfMostRecentPushRequirement()

    assert requirement.name == "RequireApprovalOfMostRecentPush"
    assert (
        requirement.description
        == "Validates whether a ruleset requires that the most recent reviewable push to a pull request is approved by somebody other than the person who pushed it."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireApprovalOfMostRecentPushRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "require"),
    [
        ([_CreatePullRequestRule(require_last_push_approval=False)], False),
        ([_OTHER_RULE, _CreatePullRequestRule(require_last_push_approval=False)], False),
        ([_CreatePullRequestRule(require_last_push_approval=True)], True),
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
@pytest.mark.parametrize(
    "response",
    [
        [_CreatePullRequestRule(require_last_push_approval=True)],
        [_CreatePullRequestRule(require_last_push_approval=False)],
    ],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The setting is nested within the pull request rule, so a branch that does not require a pull
# request has no push for it to gate. The rationale describes a default that is not being applied,
# so it is omitted along with the resolution.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DoesNotApplyWithoutPullRequestRule(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so there is no push to approve."
    )
    assert result.resolution is None
    assert result.rationale is None


# ----------------------------------------------------------------------
# The default expects the setting to be disabled, so a ruleset that enables it fails unless the
# user asked for it.
def test_EnabledByDefault():
    result = _Evaluate([_CreatePullRequestRule(require_last_push_approval=True)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_DisabledWhenRequired():
    result = _Evaluate([_CreatePullRequestRule(require_last_push_approval=False)], require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# The setting is reported only when the pull request rule carries it, so a rule whose parameters
# omit it is treated as not requiring approval rather than as unknown.
def test_MissingParameter():
    rule = _CreatePullRequestRule(require_last_push_approval=False)
    del rule["parameters"]["require_last_push_approval"]

    result = _Evaluate([rule], require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the setting when the default expectation is not met.
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(require_last_push_approval=True)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require approval of the most recent reviewable push** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when approval of the most recent push is
# required.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate([_CreatePullRequestRule(require_last_push_approval=False)], require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require approval of the most recent reviewable push** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CreatePullRequestRule(require_last_push_approval=True)], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        [_CreatePullRequestRule(require_last_push_approval=True)],
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireApprovalOfMostRecentPushRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
