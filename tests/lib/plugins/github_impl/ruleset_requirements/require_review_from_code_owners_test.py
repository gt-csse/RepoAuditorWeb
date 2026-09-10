import textwrap

import pytest

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_review_from_code_owners import (
    RequireReviewFromCodeOwnersRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.team_size import TeamSize
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue
from RepoAuditorWeb.web_experience_impl.form import CreateGroups, FieldType, ParseValues

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging"
)


# ----------------------------------------------------------------------
_RATIONALE_PREFIX = textwrap.dedent(
    """\
    The default behavior is to require that a ruleset does not request review from code
    owners, which matches GitHub's own default when a branch ruleset is created. The size of
    the team maintaining the repository overrides that default for a
    `large` team, where the expected value is
    `True` instead. This repository is being evaluated as
    `small`, so the expected value is
    `False`.
    """,
)


# ----------------------------------------------------------------------
def _CreatePullRequestRule(*, require_code_owner_review: bool) -> dict:
    return {
        "type": "pull_request",
        "ruleset_source_type": "Repository",
        "ruleset_source": "gt-csse/RepoAuditorWeb",
        "ruleset_id": 42,
        "parameters": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews_on_push": False,
            "require_code_owner_review": require_code_owner_review,
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
def _CreateModule(requirement: RequireReviewFromCodeOwnersRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    require: bool | None = None,
    team_size: TeamSize = TeamSize.Small,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RequireReviewFromCodeOwnersRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "team_size": team_size,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RequireReviewFromCodeOwnersRequirement()

    assert requirement.name == "RequireReviewFromCodeOwners"
    assert (
        requirement.description
        == "Validates whether a ruleset requires approval from the owners named in CODEOWNERS when a pull request modifies the paths that they own."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RequireReviewFromCodeOwnersRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type == (bool | None)
    assert parameters["require"].default is None


# ----------------------------------------------------------------------
# The team size decides only when the parameter is absent, so the web experience must offer a choice
# that submits the absent value rather than one that collapses it to False.
def test_ParameterIsDisplayedAsAModeThatDefersToTheTeamSize():
    requirement = RequireReviewFromCodeOwnersRequirement()

    dynamic_parameters = DynamicParameters([_CreateModule(requirement)])

    groups = CreateGroups(dynamic_parameters, {})

    field = next(
        field
        for group in groups
        for section in group.sections
        for field in section.fields
        if field.type == FieldType.RequirementMode
    )

    assert field.choices == ["skip", "use default", "require", "prohibit"]

    # The parameter is absent by default, so that is the choice the control starts on.
    assert field.value == "use default"

    arguments = ParseValues(dynamic_parameters, {field.name: field.value})

    assert arguments["MyModule"][requirement.name]["require"] is None


# ----------------------------------------------------------------------
# The expectation is derived from the team size, since a solo or small team rarely has an owner
# other than the author to name while a large team does.
@pytest.mark.parametrize(
    ("team_size", "expected"),
    [
        (TeamSize.Solo, False),
        (TeamSize.Small, False),
        (TeamSize.Large, True),
    ],
)
def test_TeamSizeDefault(team_size, expected):
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=expected)],
        team_size=team_size,
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The setting is a parameter of the pull request rule, so a branch that does not require a pull
# request requests no code owner review regardless of the team size.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_DoesNotApplyWithoutPullRequestRule(response, team_size):
    result = _Evaluate(response, team_size=team_size)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so no code owner review is requested."
    )
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize(
    "response",
    [
        [_CreatePullRequestRule(require_code_owner_review=True)],
        [_CreatePullRequestRule(require_code_owner_review=False)],
    ],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale is not None
    assert result.rationale.startswith(_RATIONALE_PREFIX)


# ----------------------------------------------------------------------
# The rationale names the team size under evaluation so that the reader can see where the expected
# value came from.
@pytest.mark.parametrize(
    ("team_size", "expected"),
    [
        (TeamSize.Solo, "`solo`, so the expected value is\n`False`."),
        (TeamSize.Small, "`small`, so the expected value is\n`False`."),
        (TeamSize.Large, "`large`, so the expected value is\n`True`."),
    ],
)
def test_RationaleNamesTeamSize(team_size, expected):
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=False)],
        team_size=team_size,
    )

    assert result.rationale is not None
    assert expected in result.rationale


# ----------------------------------------------------------------------
# A large team is expected to route each change to the people who own the paths it touches, so the
# rule being disabled is reported.
def test_DisabledForLargeTeam():
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=False)],
        team_size=TeamSize.Large,
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# The rule being enabled is reported for a small team as well, because a sole owner cannot approve
# their own pull request and would be blocked by it.
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small])
def test_EnabledForSmallTeam(team_size):
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=True)],
        team_size=team_size,
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The parameter is absent from the rule when the ruleset was created without it, which is treated as
# the rule not being required rather than as an error in the response.
def test_MissingParameter():
    rule = _CreatePullRequestRule(require_code_owner_review=True)
    del rule["parameters"]["require_code_owner_review"]

    result = _Evaluate([rule], team_size=TeamSize.Small)

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# An explicit value takes precedence over the value implied by the team size, so a small team can
# state that the rule is required.
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_RequireOverridesTeamSize(team_size):
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=True)],
        require=True,
        team_size=team_size,
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# The override applies in the other direction as well, so a large team can state that the rule must
# stay off.
@pytest.mark.parametrize("team_size", [TeamSize.Solo, TeamSize.Small, TeamSize.Large])
def test_RequireInvertsExpectation(team_size):
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=False)],
        require=False,
        team_size=team_size,
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# A large team that does not require the rule reports it when the rule is enabled, which the team
# size alone would have accepted.
def test_RequireReportsEnabledRule():
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=True)],
        require=False,
        team_size=TeamSize.Large,
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolutionChecks():
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=False)],
        team_size=TeamSize.Large,
    )

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Check the **Require review from Code Owners** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution names the action that satisfies the requirement rather than a fixed one.
def test_ErrorResolutionClears():
    result = _Evaluate(
        [_CreatePullRequestRule(require_code_owner_review=True)],
        team_size=TeamSize.Small,
    )

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Clear the **Require review from Code Owners** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
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
        [_CreatePullRequestRule(require_code_owner_review=False)],
        team_size=TeamSize.Large,
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
        [_CreatePullRequestRule(require_code_owner_review=False)],
        team_size=TeamSize.Large,
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = RequireReviewFromCodeOwnersRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": None})

    assert result.result == EvaluateResultValue.Skipped
