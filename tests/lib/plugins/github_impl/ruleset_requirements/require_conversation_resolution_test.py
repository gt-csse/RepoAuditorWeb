import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_conversation_resolution import (
    RequireConversationResolutionRequirement,
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
    The default behavior is to require that a ruleset requires conversation resolution
    before merging.

    Note that this differs from GitHub's own default when a branch ruleset is created, where
    the setting is not selected even once the pull request rule is enabled.

    ## Reasons for this Default

    - Review comments are how a reviewer records what they want changed, and nothing else in
      the ruleset makes acting on them a condition of merging. An approval can be granted
      alongside comments that were never addressed, so without this setting the feedback
      carries no weight at merge time.
    - The gap it closes is a quiet one. A pull request with open threads looks the same at
      the merge button as one with none, so a comment is lost through inattention rather
      than through a decision to ignore it, and the loss is invisible once the branch is
      deleted.
    - Resolution is an acknowledgment rather than an agreement. A thread may be closed
      because the change was made, because the reviewer was answered, or because the
      suggestion was declined with a reason, so the setting forces the conversation to reach
      an end rather than forcing the author to comply.
    - It leaves a record of that end. Every thread on a merged pull request carries a
      deliberate close, which is what makes the review readable later by somebody asking why
      a suggestion was not taken.
    - The cost is bounded by the number of comments, and a thread that was addressed is
      closed with one click. A pull request that drew no review comments is unaffected.

    ## Reasons to Override this Default

    - The project uses review comments for remarks that are not requests, such as praise,
      questions asked out of curiosity, or notes about adjacent code, where requiring a
      close on each turns commenting into administrative work and discourages the remarks
      themselves.
    - Threads outlive the code they were attached to. A comment on a commit that a force
      push removed can become unresolvable while still blocking the merge, which leaves the
      author to reopen the pull request or seek a bypass to land work that is otherwise
      ready.
    - Resolving a thread requires write access or authorship of the pull request, so an
      outside contributor cannot close a thread that a reviewer left open, and the merge
      waits on somebody with permission rather than on the change being ready.
    - The signal degrades where the setting is enforced without agreement on what a
      resolution means. If the habit is to close threads in bulk to unblock a merge, the
      requirement records compliance rather than that the comments were read.

    Note that GitHub applies the setting to the review comment threads on the **Files
    changed** tab rather than to every comment on the pull request, so a remark left on the
    **Conversation** tab does not block the merge.

    Note also that actors granted bypass permission on the ruleset may merge with threads
    still open, so the setting describes the path that contributors take rather than one
    that cannot be circumvented.
    """,
)


# ----------------------------------------------------------------------
def _CreatePullRequestRule(*, required_review_thread_resolution: bool) -> dict:
    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": False,
            "require_last_push_approval": False,
            "required_review_thread_resolution": required_review_thread_resolution,
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
def _CreateModule(requirement: RequireConversationResolutionRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    prohibit: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireConversationResolutionRequirement()

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
    requirement = RequireConversationResolutionRequirement()

    assert requirement.name == "RequireConversationResolution"
    assert (
        requirement.description
        == "Validates whether a ruleset requires that every review comment thread on a pull request is marked as resolved before the pull request may be merged."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireConversationResolutionRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("response", "prohibit"),
    [
        ([_CreatePullRequestRule(required_review_thread_resolution=True)], False),
        ([_OTHER_RULE, _CreatePullRequestRule(required_review_thread_resolution=True)], False),
        ([_CreatePullRequestRule(required_review_thread_resolution=False)], True),
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
@pytest.mark.parametrize(
    "response",
    [
        [_CreatePullRequestRule(required_review_thread_resolution=True)],
        [_CreatePullRequestRule(required_review_thread_resolution=False)],
    ],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The setting is nested within the pull request rule, so a branch that does not require a pull
# request hosts no review comment threads for it to govern. The rationale describes a default that
# is not being applied, so it is omitted along with the resolution.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DoesNotApplyWithoutPullRequestRule(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so there are no conversations to resolve."
    )
    assert result.resolution is None
    assert result.rationale is None


# ----------------------------------------------------------------------
# The pull request rule may be enabled without requiring conversation resolution, which is GitHub's
# own default and allows a merge while review comments remain unaddressed.
def test_PullRequestRuleWithoutResolution():
    result = _Evaluate([_CreatePullRequestRule(required_review_thread_resolution=False)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_RequiredWhenProhibited():
    result = _Evaluate(
        [_CreatePullRequestRule(required_review_thread_resolution=True)],
        prohibit=True,
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The setting is reported only when the pull request rule carries it, so a rule whose parameters
# omit it is treated as not requiring resolution rather than as unknown.
def test_MissingParameter():
    rule = _CreatePullRequestRule(required_review_thread_resolution=True)
    del rule["parameters"]["required_review_thread_resolution"]

    result = _Evaluate([rule])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(required_review_thread_resolution=False)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require conversation resolution before merging** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the setting when conversation resolution must not be
# required.
def test_ErrorResolutionWhenProhibited():
    result = _Evaluate(
        [_CreatePullRequestRule(required_review_thread_resolution=True)],
        prohibit=True,
    )

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require conversation resolution before merging** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate(
        [_CreatePullRequestRule(required_review_thread_resolution=False)],
        branch="trunk",
    )

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        [_CreatePullRequestRule(required_review_thread_resolution=False)],
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireConversationResolutionRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "prohibit": False})

    assert result.result == EvaluateResultValue.Skipped
