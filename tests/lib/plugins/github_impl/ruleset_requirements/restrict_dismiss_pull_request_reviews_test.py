import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_dismiss_pull_request_reviews import (
    RestrictDismissPullRequestReviewsRequirement,
)
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
    The default behavior is to require that a ruleset restricts review dismissal to named
    actors and that it names at most 0 of them.
    """,
)


# ----------------------------------------------------------------------
def _CreateActor(actor_id: int, actor_type: str = "Team") -> dict:
    return {"id": actor_id, "type": actor_type}


# ----------------------------------------------------------------------
def _CreatePullRequestRule(dismissal_restriction: dict | None = None) -> dict:
    parameters = {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": False,
        "require_last_push_approval": False,
        "required_review_thread_resolution": False,
    }

    # GitHub omits the setting rather than reporting a disabled restriction, so the absence of the
    # key is what a ruleset that does not restrict dismissal actually looks like.
    if dismissal_restriction is not None:
        parameters["dismissal_restriction"] = dismissal_restriction

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
def _CreateModule(requirement: RestrictDismissPullRequestReviewsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: list[dict],
    *,
    prohibit: bool = False,
    value: int = 0,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = RestrictDismissPullRequestReviewsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "branch": branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "prohibit": prohibit, "value": value},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = RestrictDismissPullRequestReviewsRequirement()

    assert requirement.name == "RestrictDismissPullRequestReviews"
    assert (
        requirement.description
        == "Validates whether a ruleset restricts review dismissal to named actors and how many actors it grants that ability to."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = RestrictDismissPullRequestReviewsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit", "value"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False
    assert parameters["value"].type is int
    assert parameters["value"].default == 0


# ----------------------------------------------------------------------
# The default requires the restriction to be enabled while naming no actors, which is the narrowest
# configuration the setting offers.
def test_EnabledWithNoActors():
    result = _Evaluate([_CreatePullRequestRule({"enabled": True})])

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# An omitted roster and an empty one describe the same ruleset.
def test_EnabledWithEmptyActorList():
    result = _Evaluate([_CreatePullRequestRule({"enabled": True, "allowed_actors": []})])

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# The restriction is a setting of the pull request rule, so a branch that does not require a pull
# request collects no reviews for it to protect.
@pytest.mark.parametrize("response", [[], [_OTHER_RULE]])
def test_DoesNotApplyWithoutPullRequestRule(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The ruleset does not require a pull request before merging, so there are no reviews to dismiss."
    )
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize(
    "response",
    [[_CreatePullRequestRule({"enabled": True})], [_CreatePullRequestRule(None)]],
)
def test_Rationale(response):
    result = _Evaluate(response)

    assert result.rationale is not None
    assert result.rationale.startswith(_RATIONALE_PREFIX)


# ----------------------------------------------------------------------
# GitHub omits the setting when the restriction is not in use, which is the state the default is
# expected to move away from.
def test_MissingDismissalRestriction():
    result = _Evaluate([_CreatePullRequestRule(None)])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An explicitly disabled restriction and an absent one describe the same ruleset.
def test_DisabledDismissalRestriction():
    result = _Evaluate([_CreatePullRequestRule({"enabled": False})])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# The roster is a maximum, so naming an actor exceeds a default that permits none.
def test_ActorsNamedWhenNoneExpected():
    result = _Evaluate([_CreatePullRequestRule({"enabled": True, "allowed_actors": [_CreateActor(1)]})])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset allows 1 actor(s) to dismiss reviews, but the requirement specifies it must be at most 0."
    )


# ----------------------------------------------------------------------
def test_TooManyActors():
    result = _Evaluate(
        [
            _CreatePullRequestRule(
                {
                    "enabled": True,
                    "allowed_actors": [_CreateActor(1), _CreateActor(2, "User"), _CreateActor(3)],
                },
            )
        ],
        value=2,
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The ruleset allows 3 actor(s) to dismiss reviews, but the requirement specifies it must be at most 2."
    )


# ----------------------------------------------------------------------
# The count is a maximum, so a ruleset naming fewer actors than the requirement permits satisfies
# it.
def test_FewerActorsThanPermitted():
    result = _Evaluate(
        [_CreatePullRequestRule({"enabled": True, "allowed_actors": [_CreateActor(1)]})], value=3
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
# The prohibit parameter inverts the expectation, so a ruleset that does not restrict dismissal is
# the one that satisfies it.
@pytest.mark.parametrize("dismissal_restriction", [None, {"enabled": False}])
def test_ProhibitSucceedsWhenNotRestricted(dismissal_restriction):
    result = _Evaluate([_CreatePullRequestRule(dismissal_restriction)], prohibit=True)

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_ProhibitFailsWhenRestricted():
    result = _Evaluate([_CreatePullRequestRule({"enabled": True})], prohibit=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# The roster grants nobody anything on a ruleset that was required not to enable the restriction, so
# the count is not applied when the restriction is prohibited.
def test_ProhibitIgnoresActorCount():
    result = _Evaluate(
        [_CreatePullRequestRule({"enabled": False, "allowed_actors": [_CreateActor(1), _CreateActor(2)]})],
        prohibit=True,
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate([_CreatePullRequestRule(None)])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Check the **Restrict who can dismiss pull request reviews** checkbox.
        5) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# Enabling the restriction and clearing it are different actions, so the resolution names the one
# that satisfies the requirement.
def test_ProhibitResolution():
    result = _Evaluate([_CreatePullRequestRule({"enabled": True})], prohibit=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Clear the **Restrict who can dismiss pull request reviews** checkbox.
        5) Click the **Save changes** button at the bottom of the page.

        See [Available rules for rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# Removing actors from the roster is a different action from enabling the restriction, so it has a
# resolution of its own that names the count that satisfies the requirement.
def test_TooManyActorsResolution():
    result = _Evaluate(
        [_CreatePullRequestRule({"enabled": True, "allowed_actors": [_CreateActor(1), _CreateActor(2)]})],
        value=1,
    )

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the name of the ruleset that targets `main`.
        3) Click **Show additional settings** beneath **Require a pull request before merging** in the **Branch rules** section.
        4) Remove actors listed beneath the **Restrict who can dismiss pull request reviews** checkbox until at most 1 remain.
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
    requirement = RestrictDismissPullRequestReviewsRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement), {}, {"skip": True, "prohibit": False, "value": 0}
    )

    assert result.result == EvaluateResultValue.Skipped
