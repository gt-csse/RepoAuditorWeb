import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.dismiss_stale_pull_request_approvals import (
    DismissStalePullRequestApprovalsRequirement,
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
    The default behavior is to require that a ruleset dismisses stale pull request approvals
    when new commits are pushed.

    Note that this differs from GitHub's own default when a branch ruleset is created, where
    the setting is not selected even once the pull request rule is enabled.

    ## Reasons for this Default

    - An approval is a statement about a diff rather than about a branch. Without this
      setting the approval remains attached to the pull request while the code beneath it is
      replaced, so the merge is authorized by a review of something that is no longer what
      gets merged.
    - The gap it closes is the one a hurried author or a bad actor would use. A pull request
      can be opened small, approved, and then extended with a further commit, and the merge
      button stays enabled throughout, so the approval requirement ends up satisfied by code
      that nobody agreed to.
    - It is what keeps the approval count honest. Requiring approvals establishes how many
      people must agree, and dismissing stale ones establishes that they agreed to the
      current state, so without it the count measures how many people once looked rather
      than how many endorse what will land.
    - Dismissal is driven by the diff changing rather than by any push, so a comment or a
      push that leaves the content identical does not discard the review. Approvals are
      dismissed when a contributor pushes new changes, clicks **Update branch**, or a
      related pull request is merged into the target branch and moves the merge base.
    - The cost falls on the pull requests that changed the most. A change that is approved
      and merged unaltered is never affected, and re-approving a small follow-up commit is
      usually a glance rather than a repeat of the original review.

    ## Reasons to Override this Default

    - The project's pull requests routinely receive many small commits after approval, such
      as review feedback applied one commit at a time, where repeated dismissal turns a
      single review into a sequence of them and trains reviewers to re-approve without
      rereading.
    - The target branch moves quickly enough that merge base changes dismiss approvals on
      pull requests that did not themselves change, in which case reviews are discarded for
      a reason unrelated to the change under review.
    - **Require approval of the most recent reviewable push** is used instead. That setting
      keeps existing approvals and requires only that someone other than the person who made
      the most recent changes approves, which preserves earlier review effort while still
      ensuring another person saw the latest commits.
    - The repository requires no approvals at all, such as one maintained by a single
      person, where there is no approval for the setting to dismiss.

    Note that the setting governs the approvals GitHub has already collected rather than who
    may grant them. It does not prevent the same reviewer from approving again immediately,
    so it ensures that an approval refers to the current diff rather than that the diff
    received a fresh pair of eyes.

    Note also that actors granted bypass permission on the ruleset may merge without
    satisfying the approval requirement at all, so the setting describes the path that
    contributors take rather than one that cannot be circumvented.
    """,
)


# ----------------------------------------------------------------------
def _CreatePullRequestRule(*, dismiss_stale_reviews_on_push: bool) -> dict:
    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews_on_push": dismiss_stale_reviews_on_push,
            "require_code_owner_review": False,
            "require_last_push_approval": False,
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
def _CreateModule(requirement: DismissStalePullRequestApprovalsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    disallow: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = DismissStalePullRequestApprovalsRequirement()

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
    requirement = DismissStalePullRequestApprovalsRequirement()

    assert requirement.name == "DismissStalePullRequestApprovals"
    assert (
        requirement.description
        == "Validates whether a ruleset dismisses the approving reviews on a pull request when new commits change the code that those reviews were granted against."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = DismissStalePullRequestApprovalsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "disallow"),
    [
        ([_CreatePullRequestRule(dismiss_stale_reviews_on_push=True)], False),
        ([_OTHER_RULE, _CreatePullRequestRule(dismiss_stale_reviews_on_push=True)], False),
        ([_CreatePullRequestRule(dismiss_stale_reviews_on_push=False)], True),
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
@pytest.mark.parametrize(
    "response",
    [
        [_CreatePullRequestRule(dismiss_stale_reviews_on_push=True)],
        [_CreatePullRequestRule(dismiss_stale_reviews_on_push=False)],
    ],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The setting is nested within the pull request rule, so a branch that does not require a pull
# request collects no approvals for it to dismiss. The rationale describes a default that is not
# being applied, so it is omitted along with the resolution.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DoesNotApplyWithoutPullRequestRule(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so there are no approvals to dismiss."
    )
    assert result.resolution is None
    assert result.rationale is None


# ----------------------------------------------------------------------
# The pull request rule may be enabled without dismissing stale approvals, which is GitHub's own
# default and leaves an approval attached to code that was replaced after it was granted.
def test_PullRequestRuleWithoutDismissal():
    result = _Evaluate([_CreatePullRequestRule(dismiss_stale_reviews_on_push=False)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_DismissedWhenDisallowed():
    result = _Evaluate([_CreatePullRequestRule(dismiss_stale_reviews_on_push=True)], disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The setting is reported only when the pull request rule carries it, so a rule whose parameters
# omit it is treated as not dismissing rather than as unknown.
def test_MissingParameter():
    rule = _CreatePullRequestRule(dismiss_stale_reviews_on_push=True)
    del rule["parameters"]["dismiss_stale_reviews_on_push"]

    result = _Evaluate([rule])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(dismiss_stale_reviews_on_push=False)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Dismiss stale pull request approvals when new commits are pushed** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the setting when stale approvals must not be dismissed.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate([_CreatePullRequestRule(dismiss_stale_reviews_on_push=True)], disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Dismiss stale pull request approvals when new commits are pushed** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CreatePullRequestRule(dismiss_stale_reviews_on_push=False)], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        [_CreatePullRequestRule(dismiss_stale_reviews_on_push=False)],
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = DismissStalePullRequestApprovalsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
