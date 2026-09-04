import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_issues import (
    SupportIssuesRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-issues"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository's issue tracker is enabled, which
    matches the state of a newly created repository.

    ## Reasons for this Default

    - Issues are the only place a user without write access can report a defect. With the
      tracker disabled, the repository presents no supported way to report one, so reports
      arrive as unsolicited pull requests, email, or nothing at all.
    - Issue numbers share a namespace with pull requests and are the target of GitHub's
      cross-referencing: `#<number>` in a commit message or comment links to the issue, and a
      pull request body containing `Fixes #<number>` closes it on merge. Disabling the tracker
      removes the record that this linking is built around.
    - Issues are what populate the repository's history of known defects, so a search for a
      symptom finds the previous report and its resolution. Discussion held elsewhere is not
      searchable from the repository.
    - The tracker is the surface that issue templates and forms configure. A repository that
      ships `.github/ISSUE_TEMPLATE` content but has the feature disabled presents contributors
      with configuration that never takes effect.

    ## Reasons to Override this Default

    - The repository does not accept contributions or bug reports, in which case an enabled
      tracker invites reports that no one will triage. This is the case GitHub gives for
      turning the feature off.
    - Tracking happens somewhere else (an external tracker, or a separate issues-only
      repository used because GitHub does not provide issues-only access permissions), and two
      trackers would split reports between them.
    - The repository is a mirror or a published artifact whose source of truth is elsewhere, so
      reports filed against it cannot be acted upon.

    Note that before disabling the tracker outright, restricting it is often the narrower fix:
    the **Issues** dropdown offers **Collaborators only**, which keeps the tracker and its
    history while limiting who can open new issues. Also note that disabling hides existing
    issues rather than erasing them; re-enabling the feature restores them.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SupportIssuesRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = SupportIssuesRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SupportIssuesRequirement()

    assert requirement.name == "SupportIssues"
    assert (
        requirement.description
        == "Validates whether the repository's issue tracker is enabled; issues are where bug reports, tasks, and feature requests are filed and referenced."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
# The tracker is enabled on a newly created repository, so the parameter names the override rather
# than the default, keeping it a flag that defaults to off.
def test_GetParameters():
    parameters = SupportIssuesRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("has_issues", "disallow"),
    [(True, False), (False, True)],
)
def test_MatchingStatus(has_issues, disallow):
    result = _Evaluate({"has_issues": has_issues}, disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"has_issues": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"has_issues": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"has_issues": False})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Check the **Issues** checkbox.

        See [Disabling issues]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to uncheck the setting when the tracker must be disabled.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate({"has_issues": True}, disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Uncheck the **Issues** checkbox.

        See [Disabling issues]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"has_issues": False}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_NoIssuesWhenRequired():
    result = _Evaluate({"has_issues": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_IssuesWhenDisallowed():
    result = _Evaluate({"has_issues": True}, disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An absent 'has_issues' key is treated as False, so it fails the default requirement of True.
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
    requirement = SupportIssuesRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
