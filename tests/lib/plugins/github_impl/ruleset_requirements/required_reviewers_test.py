import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.required_reviewers import (
    RequiredReviewersRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.team_size import TeamSize
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#required-reviewers"
)


# ----------------------------------------------------------------------
_RATIONALE_PREFIX = textwrap.dedent(
    """\
    The default behavior is to require the number of reviewing teams implied by the size of
    the team maintaining the repository, which is 0 for a
    `solo` team, 0 for a `small`
    team, and at least 1 for a `large` team.
    This repository is being evaluated as `large`, so the expected value is
    1.
    """,
)


# ----------------------------------------------------------------------
def _CreateReviewer(team_id: int, minimum_approvals: int = 1) -> dict:
    return {
        "reviewer": {"id": team_id, "type": "Team"},
        "minimum_approvals": minimum_approvals,
        "file_patterns": ["src/**"],
    }


# ----------------------------------------------------------------------
def _CreatePullRequestRule(reviewers: list[dict] | None = None) -> dict:
    parameters = {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": False,
        "require_code_owner_review": False,
        "require_last_push_approval": False,
        "required_review_thread_resolution": False,
    }

    # GitHub omits the setting rather than reporting an empty roster, so the absence of the key is
    # what a ruleset that names no teams actually looks like.
    if reviewers is not None:
        parameters["required_reviewers"] = reviewers

    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": parameters,
    }


_OTHER_RULE = {
    "type": "non_fast_forward",
    "ruleset_source_type": "Repository",
    "ruleset_source": "gt-csse/RepoAuditorWeb",
    "ruleset_id": 42,
    "parameters": {},
}


# ----------------------------------------------------------------------
def _CreateModule(requirement: RequiredReviewersRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    value: int | None = None,
    team_size: TeamSize = TeamSize.Large,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequiredReviewersRequirement()

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
    requirement = RequiredReviewersRequirement()

    assert requirement.name == "RequiredReviewers"
    assert (
        requirement.description
        == "Validates the number of teams that a ruleset requires to review pull requests changing the file patterns each team is named for."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequiredReviewersRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type == (int | None)
    assert parameters["value"].default is None


# ----------------------------------------------------------------------
# The rule names teams rather than people, so a solo maintainer cannot use it at all and a small
# team has no division of ownership for it to express.
@pytest.mark.parametrize(
    ("team_size", "reviewers"),
    [
        (TeamSize.Solo, None),
        (TeamSize.Small, None),
        (TeamSize.Large, [_CreateReviewer(1)]),
    ],
)
def test_TeamSizeDefault(team_size, reviewers):
    result = _Evaluate([_CreatePullRequestRule(reviewers)], team_size=team_size)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The teams are a setting of the pull request rule, so a branch that does not require a pull
# request requests no reviews for it to govern regardless of the team size.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_DoesNotApplyWithoutPullRequestRule(response, team_size):
    result = _Evaluate(response, team_size=team_size)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so no reviews are requested."
    )
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize(
    "response",
    [[_CreatePullRequestRule([_CreateReviewer(1)])], [_CreatePullRequestRule(None)]],
)
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
        (TeamSize.Small, "`small`, so the expected value is\n0."),
        (TeamSize.Large, "`large`, so the expected value is\n1."),
    ],
)
def test_RationaleNamesTeamSize(team_size, expected):
    result = _Evaluate([_CreatePullRequestRule([_CreateReviewer(1)])], team_size=team_size)

    assert result.rationale is not None
    assert expected in result.rationale


# ----------------------------------------------------------------------
# GitHub omits the setting when no teams are named, which is the state a large team is expected to
# move away from.
def test_MissingReviewers():
    result = _Evaluate([_CreatePullRequestRule(None)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires reviews from 0 team(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
# An empty roster and an absent setting describe the same ruleset, so both are reported the same
# way.
def test_EmptyReviewers():
    result = _Evaluate([_CreatePullRequestRule([])])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires reviews from 0 team(s), but the requirement specifies it must be at least 1."
    )


# ----------------------------------------------------------------------
def test_TooFewReviewers():
    result = _Evaluate([_CreatePullRequestRule([_CreateReviewer(1), _CreateReviewer(2)])], value=3)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires reviews from 2 team(s), but the requirement specifies it must be at least 3."
    )


# ----------------------------------------------------------------------
# The count is a minimum, so a ruleset naming more teams than the requirement asks for satisfies
# it; which teams a repository names is its own business.
def test_MoreReviewersThanRequired():
    result = _Evaluate([_CreatePullRequestRule([_CreateReviewer(1), _CreateReviewer(2)])])

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# A team is counted whatever its approval threshold, because a team entered with zero approvals is
# still a team the ruleset names.
def test_ReviewerWithZeroApprovals():
    result = _Evaluate([_CreatePullRequestRule([_CreateReviewer(1, minimum_approvals=0)])])

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# A requirement of no teams is a statement that the setting must not be used rather than a minimum
# that any roster exceeds.
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small])
def test_ReviewersNamedWhenNoneExpected(team_size):
    result = _Evaluate([_CreatePullRequestRule([_CreateReviewer(1)])], team_size=team_size)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset requires reviews from 1 team(s), but the requirement specifies that it must not name any."
    )


# ----------------------------------------------------------------------
# An explicit value takes precedence over the count implied by the team size.
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_ValueOverridesTeamSize(team_size):
    result = _Evaluate(
        [_CreatePullRequestRule([_CreateReviewer(1), _CreateReviewer(2)])], value=2, team_size=team_size
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# A value of zero is an override rather than an absent one, so it is honored for a large team whose
# size would otherwise imply that a team must be named.
def test_ValueOfZero():
    result = _Evaluate([_CreatePullRequestRule(None)], value=0, team_size=TeamSize.Large)

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(None)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Check the **Require review from specific teams** checkbox.
        5) Click **Add reviewer** until at least 1 team(s) are listed, selecting each one in the **Reviewer** dropdown and entering the **File patterns** it is responsible for.
        6) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution names the count that satisfies the requirement rather than a fixed one.
def test_ErrorResolutionUsesExpectedCount():
    result = _Evaluate([_CreatePullRequestRule(None)], value=4)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Check the **Require review from specific teams** checkbox.
        5) Click **Add reviewer** until at least 4 team(s) are listed, selecting each one in the **Reviewer** dropdown and entering the **File patterns** it is responsible for.
        6) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# Removing a roster and adding to one are different actions, so the resolution differs from the one
# that asks for teams to be added.
def test_NoneExpectedResolution():
    result = _Evaluate([_CreatePullRequestRule([_CreateReviewer(1)])], team_size=TeamSize.Small)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Clear the **Require review from specific teams** checkbox, removing every team listed beneath it.
        5) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A ruleset may target a branch other than 'main', so the resolution names the branch that was
# queried.
def test_ResolutionUsesBranchName():
    result = _Evaluate([_CreatePullRequestRule(None)], branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate([_CreatePullRequestRule(None)], url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequiredReviewersRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "value": None})

    assert result.result == EvaluateResultValue.Skipped
