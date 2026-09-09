import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_pull_requests import (
    RequirePullRequestsRequirement,
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
    The default behavior is to require that a ruleset mandates a pull request before
    merging.

    Note that this differs from GitHub's own default when a branch ruleset is created, where
    the rule is not selected.

    ## Reasons for this Default

    - A direct push reaches the branch without producing anything that can be examined
      first. The rule does not add a gate so much as create the object the rest of the
      repository's process attaches to: a review, an approval, a status check, and a
      conversation all refer to a pull request, so a change that never opens one is a change
      those controls cannot describe.
    - The rule is what makes the other rules meaningful. Required status checks and required
      reviews constrain how a pull request merges, so a branch that still accepts direct
      pushes leaves a path that bypasses them entirely rather than a path that is merely
      less scrutinized.
    - The record survives the merge. A pull request retains the discussion, the reviewers,
      and the checks that ran against the change, so the reason a commit was accepted
      remains recoverable later, whereas a direct push leaves only the commit message.
    - Enforcing it at the branch is what makes it reliable. A project that expects pull
      requests by convention depends on every contributor remembering under time pressure,
      and the pushes that skip the process are the ones made in a hurry rather than the ones
      that were least important.
    - The cost is small for work that was going to be reviewed anyway. The rule requires
      only that a pull request be opened, and a ruleset that sets no required approvals
      permits the author to merge their own pull request immediately.

    ## Reasons to Override this Default

    - Automation pushes to the branch directly, such as a release workflow that commits a
      version bump or a job that regenerates checked-in artifacts, in which case a bypass
      entry for that actor is usually preferable to disabling the rule for everyone.
    - The repository is maintained by a single person for whom a pull request per change is
      a step with no reviewer at the end of it, such as a personal project or a scratch
      repository.
    - The branch receives a history produced elsewhere, such as a mirror or an import, whose
      commits cannot be routed through a pull request.

    Note that the rule constrains how a change reaches the branch rather than who may
    approve it. Whether a pull request needs an approving review, a code owner's approval,
    or resolved conversations is governed by that rule's own settings, so a ruleset that
    requires a pull request and nothing else still permits a change to merge unreviewed.

    Note also that actors granted bypass permission on the ruleset may push to the branch
    directly, so the rule describes the path that contributors take rather than one that
    cannot be circumvented.
    """,
)


# ----------------------------------------------------------------------
_PULL_REQUEST_RULE = {
    "type": "pull_request",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": False,
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
def _CreateModule(requirement: RequirePullRequestsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    disallow: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequirePullRequestsRequirement()

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
    requirement = RequirePullRequestsRequirement()

    assert requirement.name == "RequirePullRequests"
    assert (
        requirement.description
        == "Validates whether a ruleset requires that changes to branches matching its pattern arrive through a pull request rather than a direct push."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequirePullRequestsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "disallow"),
    [
        ([_PULL_REQUEST_RULE], False),
        ([_OTHER_RULE, _PULL_REQUEST_RULE], False),
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
@pytest.mark.parametrize("response", [[_PULL_REQUEST_RULE], [_OTHER_RULE]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The endpoint reports only the rules that apply, so a branch whose rules do not include the pull
# request rule is one that accepts direct pushes.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_NotRequiredWhenRequired(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_RequiredWhenDisallowed():
    result = _Evaluate([_PULL_REQUEST_RULE], disallow=True)

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
        3) Check the **Require a pull request before merging** checkbox in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the rule when pull requests must not be required.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate([_PULL_REQUEST_RULE], disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require a pull request before merging** checkbox in the **Branch rules** section.
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
    requirement = RequirePullRequestsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
