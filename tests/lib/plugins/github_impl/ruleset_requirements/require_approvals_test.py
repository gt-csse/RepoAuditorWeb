import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_approvals import (
    RequireApprovalsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.team_size import TeamSize
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE_PREFIX = textwrap.dedent(
    """\
    The default behavior is to require the number of approving reviews implied by the size
    of the team maintaining the repository, which is 0 for a
    `solo` team, 1 for a `small`
    team, and 2 for a `large` team. This
    repository is being evaluated as `small`, so the expected value is
    1.
    """,
)


# ----------------------------------------------------------------------
def _CreatePullRequestRule(required_approving_review_count: int) -> dict:
    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "required_approving_review_count": required_approving_review_count,
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
def _CreateModule(requirement: RequireApprovalsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    value: int | None = None,
    team_size: TeamSize = TeamSize.Small,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireApprovalsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "team_size": team_size,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "value": value},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireApprovalsRequirement()

    assert requirement.name == "RequireApprovals"
    assert (
        requirement.description
        == "Validates the number of approving reviews that a ruleset requires before a pull request targeting branches matching its pattern can be merged."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireApprovalsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type == (int | None)
    assert parameters["value"].default is None


# ----------------------------------------------------------------------
# The expected count is derived from the team size, since a solo maintainer has nobody available to
# approve while a larger team does.
@pytest.mark.parametrize(
    ("team_size", "expected"),
    [
        (TeamSize.Solo, 0),
        (TeamSize.Small, 1),
        (TeamSize.Large, 2),
    ],
)
def test_TeamSizeDefault(team_size, expected):
    result = _Evaluate([_CreatePullRequestRule(expected)], team_size=team_size)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The count is a setting of the pull request rule, so a branch that does not require a pull request
# collects no approvals for it to govern regardless of the team size.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_DoesNotApplyWithoutPullRequestRule(response, team_size):
    result = _Evaluate(response, team_size=team_size)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so no approvals are collected."
    )
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize("response", [[_CreatePullRequestRule(1)], [_CreatePullRequestRule(0)]])
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale is not None
    assert result.rationale.startswith(_RATIONALE_PREFIX)


# ----------------------------------------------------------------------
# The rationale names the team size under evaluation so that the reader can see where the expected
# count came from.
@pytest.mark.parametrize(
    ("team_size", "expected"),
    [
        (TeamSize.Solo, "`solo`, so the expected value is\n0."),
        (TeamSize.Small, "`small`, so the expected value is\n1."),
        (TeamSize.Large, "`large`, so the expected value is\n2."),
    ],
)
def test_RationaleNamesTeamSize(team_size, expected):
    result = _Evaluate([_CreatePullRequestRule(0)], team_size=team_size)

    assert result.rationale is not None
    assert expected in result.rationale


# ----------------------------------------------------------------------
# The pull request rule may be enabled while requiring no approvals, which is GitHub's own default
# and is not sufficient for a team that has reviewers available.
def test_PullRequestRuleWithoutApprovals():
    result = _Evaluate([_CreatePullRequestRule(0)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == ("The repository's value is '0', but the requirement specifies it must be '1'.")


# ----------------------------------------------------------------------
def test_TooFewApprovals():
    result = _Evaluate([_CreatePullRequestRule(1)], team_size=TeamSize.Large)

    assert result.result == EvaluateResultValue.Error
    assert result.context == ("The repository's value is '1', but the requirement specifies it must be '2'.")


# ----------------------------------------------------------------------
# A count higher than the requirement is reported as well, because a solo maintainer cannot satisfy
# a rule that expects somebody else to approve.
def test_TooManyApprovals():
    result = _Evaluate([_CreatePullRequestRule(2)], team_size=TeamSize.Solo)

    assert result.result == EvaluateResultValue.Error
    assert result.context == ("The repository's value is '2', but the requirement specifies it must be '0'.")


# ----------------------------------------------------------------------
# An explicit value takes precedence over the count implied by the team size.
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_ValueOverridesTeamSize(team_size):
    result = _Evaluate([_CreatePullRequestRule(3)], value=3, team_size=team_size)

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# A value of zero is an override rather than an absent one, so it is honored even for a team whose
# size implies a higher count.
def test_ValueOfZero():
    result = _Evaluate([_CreatePullRequestRule(0)], value=0, team_size=TeamSize.Large)

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(0)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Set the **Required approvals** dropdown beneath **Require a pull request before merging** to 1.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution names the count that satisfies the requirement rather than a fixed one.
def test_ErrorResolutionUsesExpectedCount():
    result = _Evaluate([_CreatePullRequestRule(0)], team_size=TeamSize.Large)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Set the **Required approvals** dropdown beneath **Require a pull request before merging** to 2.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CreatePullRequestRule(0)], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate([_CreatePullRequestRule(0)], url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireApprovalsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "value": None})

    assert result.result == EvaluateResultValue.Skipped
