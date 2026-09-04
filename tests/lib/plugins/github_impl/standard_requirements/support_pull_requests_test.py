import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_pull_requests import (
    SupportPullRequestsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-pull-requests"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository's pull requests are enabled, which
    matches the state of a newly created repository.

    ## Reasons for this Default

    - Pull requests are the only way a user without write access can propose a change. With
      them disabled, the repository presents no supported route for an outside contribution,
      so a fix that someone has already written cannot be offered.
    - Pull requests are where review happens: line comments, requested changes, and approvals
      are attached to the proposal rather than to the commits that result. Disabling them
      removes the record of why a change was accepted in the form it was.
    - Branch protection and rulesets are largely enforced through pull requests, since required
      reviews, required status checks, and merge queues all gate the merge of a pull request.
      A repository that disables the feature cannot enforce those rules on the way in.
    - Pull request numbers share a namespace with issues and participate in GitHub's
      cross-referencing, so `Fixes #<number>` in a pull request body closes the issue on merge.
      Removing the feature removes the link between reported work and the change that resolved
      it.
    - The feature is the surface that a pull request template configures. A repository that
      ships `.github/pull_request_template.md` but has the feature disabled presents
      configuration that never takes effect.

    ## Reasons to Override this Default

    - The repository does not accept contributions, in which case an enabled feature invites
      proposals that no one will review. This is the case GitHub gives for turning the feature
      off.
    - The repository is a mirror or a published artifact whose source of truth is elsewhere, so
      a change made against it cannot be merged upstream and would be lost on the next
      synchronization.
    - Contributions are accepted through a different forge or a patch-based workflow such as a
      mailing list, and two intake routes would split proposals between them.

    Note that before disabling pull requests outright, restricting them is often the narrower
    fix: the **Pull requests** dropdown offers **Collaborators only**, which keeps the feature
    and its review history while limiting who can open new pull requests. Also note that
    disabling hides existing pull requests rather than erasing them; re-enabling the feature
    restores them.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SupportPullRequestsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = SupportPullRequestsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SupportPullRequestsRequirement()

    assert requirement.name == "SupportPullRequests"
    assert (
        requirement.description
        == "Validates whether the repository's pull requests are enabled; they are the only way a user without write access can contribute code."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SupportPullRequestsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("has_pull_requests", "disallow"),
    [(True, False), (False, True)],
)
def test_MatchingStatus(has_pull_requests, disallow):
    result = _Evaluate({"has_pull_requests": has_pull_requests}, disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"has_pull_requests": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"has_pull_requests": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"has_pull_requests": False})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Check the **Pull requests** checkbox.

        See [Disabling pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to uncheck the setting when pull requests must be disabled.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate({"has_pull_requests": True}, disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Uncheck the **Pull requests** checkbox.

        See [Disabling pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"has_pull_requests": False}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_NoPullRequestsWhenRequired():
    result = _Evaluate({"has_pull_requests": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_PullRequestsWhenDisallowed():
    result = _Evaluate({"has_pull_requests": True}, disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An absent 'has_pull_requests' key is treated as False, which violates the default requirement.
def test_MissingStatus():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_MissingStatusWhenDisallowed():
    result = _Evaluate({}, disallow=True)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_Skip():
    requirement = SupportPullRequestsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
