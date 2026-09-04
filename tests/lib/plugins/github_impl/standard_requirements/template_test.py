import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.template import TemplateRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/creating-and-managing-repositories"
    "/creating-a-template-repository"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository is not a template repository, which
    controls whether GitHub offers a **Use this template** button to generate new repositories
    from its contents.

    ## Reasons for this Default

    - Repositories generated from a template have unrelated histories, so changes cannot flow
      back to the template through a pull request. Offering the button on a repository that is
      not intended to be a starting point invites copies that can never contribute fixes
      upstream.
    - Generating from a template copies only the default branch unless the other branches are
      explicitly requested, so a repository whose value spans multiple branches is a poor
      template.

    ## Reasons to Override this Default

    - The repository exists to be the starting point for new repositories, in which case
      generating is preferable to forking because the result has no fork relationship and no
      inherited history.

    Note that a template repository cannot include files stored using Git LFS.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: TemplateRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = TemplateRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = TemplateRequirement()

    assert requirement.name == "Template"
    assert (
        requirement.description
        == "Validates whether the repository is a template, which generates new repositories with unrelated histories rather than forks."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = TemplateRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("is_template", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(is_template, require):
    result = _Evaluate({"is_template": is_template}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"is_template": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"is_template": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"is_template": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Template repository** checkbox.
        3) Uncheck the **Template repository** checkbox.

        See [Creating a template repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when a template is required.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"is_template": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Template repository** checkbox.
        3) Check the **Template repository** checkbox.

        See [Creating a template repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"is_template": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_TemplateWhenNotRequired():
    result = _Evaluate({"is_template": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NotTemplateWhenRequired():
    result = _Evaluate({"is_template": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An absent 'is_template' key is treated as False, so it satisfies a requirement of False.
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
    requirement = TemplateRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
