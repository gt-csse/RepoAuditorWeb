import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_projects import (
    SupportProjectsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-projects-in-a-repository"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository's projects are disabled. Note that
    this does not match the state of a newly created repository, where the setting is enabled:
    projects are advanced planning functionality that a project should opt into only if it
    intends to use it.

    ## Reasons for this Default

    - Projects are advanced functionality with a real setup cost. A board becomes useful only
      once someone defines its views, fields, and workflows, so a repository that has not done
      that work gains nothing from the setting being on.
    - An enabled but unused **Projects** tab is misleading rather than neutral. It presents
      contributors with a planning surface that suggests the project's work is tracked there,
      and an empty or stale board is worse guidance than no board.
    - The tab competes with the issue tracker as the place to look for what is being worked on.
      A project that plans in its issues and milestones is better served by directing
      contributors to a single surface.
    - A board that is populated once and then abandoned misrepresents project status
      indefinitely, since items do not fall off it the way stale issues can be closed.

    ## Reasons to Override this Default

    - The project actively plans its work on a board, in which case the setting is what
      surfaces the **Projects** tab so contributors can discover the planning that governs the
      repository rather than having to know to look at the owning organization or user.
    - The project needs issues and pull requests to carry a status beyond open and closed, which
      projects provide through priority, iteration, and custom fields that the issue tracker
      alone does not offer.
    - The project relies on automations that add an item to a board when an issue or pull
      request is opened, and keeping the repository's link to that board visible makes the
      tracking that results legible to contributors.

    Note that disabling projects removes linked projects from the repository's **Projects** tab
    but does not delete them; they remain accessible at the organization or user level and the
    tab's contents return if the setting is re-enabled. Also note that this setting governs the
    repository's link to projects rather than the projects themselves, so an organization can
    still track this repository's issues on a board that the repository does not display.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SupportProjectsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = SupportProjectsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SupportProjectsRequirement()

    assert requirement.name == "SupportProjects"
    assert (
        requirement.description
        == "Validates whether the repository's projects are enabled; the setting controls the repository's Projects tab, where projects owned by the organization or user are linked."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SupportProjectsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("has_projects", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(has_projects, require):
    result = _Evaluate({"has_projects": has_projects}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"has_projects": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"has_projects": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"has_projects": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Uncheck the **Projects** checkbox.

        See [Disabling projects in a repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when projects must be enabled.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"has_projects": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Check the **Projects** checkbox.

        See [Disabling projects in a repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"has_projects": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
# Projects are enabled on a newly created repository, so this is the state the default flags.
def test_ProjectsWhenDisallowed():
    result = _Evaluate({"has_projects": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NoProjectsWhenRequired():
    result = _Evaluate({"has_projects": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An absent 'has_projects' key is treated as False, which satisfies the default requirement.
def test_MissingStatus():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_MissingStatusWhenRequired():
    result = _Evaluate({}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_Skip():
    requirement = SupportProjectsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
