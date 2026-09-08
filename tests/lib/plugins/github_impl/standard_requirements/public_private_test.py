import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.public_private import (
    PublicPrivateRequirement,
    Values,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features"
    "/managing-repository-settings/setting-repository-visibility"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository is public.

    ## Reasons for this Default

    - A repository that cannot be read cannot be audited, cited, reproduced, or contributed
      to by anyone outside its access list. Visibility is the setting every other
      collaboration setting depends on.
    - Features that make a project legible to outsiders are available on public repositories
      regardless of plan, but require a paid plan on private ones. The community profile,
      dependency graph, and GitHub Pages are examples; a public repository gets the full
      feature set on GitHub Free, while a private one gets a limited one.
    - GitHub Actions minutes and Packages storage are not billed for public repositories, so
      a public project's continuous integration does not consume the account's included
      allowance.
    - Only public repositories are eligible for the GitHub Archive Program, so public
      visibility is what causes the code to be preserved independently of the account that
      hosts it.
    - Forking, which is how a contributor proposes a change without write access, requires
      that the contributor can read the repository.

    ## Reasons to Override this Default

    - The code is not intended for release: it contains proprietary logic, embargoed
      research, unpublished results, or material the project does not hold the rights to
      distribute.
    - The repository is subject to a policy that forbids public disclosure, such as
      export control, a data use agreement, or an institutional review requirement.
    - The repository is not ready to be read, and a premature release would misrepresent the
      project. Note that this argues for publishing later rather than for staying private,
      since visibility can be changed at any time.
    - The organization belongs to an enterprise account and uses `internal` visibility to
      share the repository across the enterprise without exposing it publicly, in which case
      `internal` is the expected value.

    Note that visibility is a poor secrecy control applied after the fact. Making a public
    repository private does not erase what was already cloned or cached, and a secret that was
    ever committed remains in the history; such a secret must be rotated rather than hidden.

    Note also that changing visibility in either direction erases the repository's stars and
    watchers, and that making a repository public makes its Actions history and logs visible
    to everyone.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: PublicPrivateRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    expected_value: Values = Values.Public,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = PublicPrivateRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "value": expected_value},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PublicPrivateRequirement()

    assert requirement.name == "PublicPrivate"
    assert (
        requirement.description
        == "Validates the repository's visibility, which determines who can see the code and which GitHub features the repository is eligible for."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = PublicPrivateRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type == Values
    assert parameters["value"].default == Values.Public


# ----------------------------------------------------------------------
# The visibility values GitHub accepts are a closed set, so an unrecognized value is rejected when
# the argument is parsed rather than reported as a failed audit.
def test_Values():
    assert list(Values) == [Values.Public, Values.Private, Values.Internal]
    assert Values.Public == "public"
    assert Values.Private == "private"
    assert Values.Internal == "internal"


# ----------------------------------------------------------------------
def test_AcceptableVisibility():
    result = _Evaluate({"visibility": "public"})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"visibility": "public"})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"visibility": "private"})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# An enterprise that shares repositories across the enterprise rather than publicly can expect
# 'internal', which the 'private' boolean cannot distinguish from 'private'.
def test_AcceptableVisibilityOtherThanDefault():
    result = _Evaluate({"visibility": "internal"}, Values.Internal)

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_UnacceptableVisibility():
    result = _Evaluate({"visibility": "private"})

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The visibility is 'private' but 'public' was expected."


# ----------------------------------------------------------------------
def test_UnacceptableVisibilityUsesExpectedValue():
    result = _Evaluate({"visibility": "public"}, Values.Internal)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The visibility is 'public' but 'internal' was expected."


# ----------------------------------------------------------------------
def test_UnacceptableVisibilityResolution():
    result = _Evaluate({"visibility": "private"})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Danger Zone** section.
        3) Click the **Change visibility** button.
        4) Select 'public'.
        5) Click the **I have read and understand these effects** button.
        6) Enter the repository's name to confirm, then click the button that completes the change.

        See [Setting repository visibility]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A missing visibility produces the same resolution as an unacceptable one, since both are fixed by
# setting the visibility to the expected value.
def test_NoVisibilityResolution():
    result = _Evaluate({}, Values.Internal)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Danger Zone** section.
        3) Click the **Change visibility** button.
        4) Select 'internal'.
        5) Click the **I have read and understand these effects** button.
        6) Enter the repository's name to confirm, then click the button that completes the change.

        See [Setting repository visibility]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"visibility": "private"}, Values.Public, "https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
@pytest.mark.parametrize("response", [{}, {"visibility": None}])
def test_NoVisibility(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "No visibility value was set."


# ----------------------------------------------------------------------
def test_Skip():
    requirement = PublicPrivateRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "value": Values.Public})

    assert result.result == EvaluateResultValue.Skipped
