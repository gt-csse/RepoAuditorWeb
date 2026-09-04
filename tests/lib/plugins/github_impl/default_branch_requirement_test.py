import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.default_branch_requirement import DefaultBranchRequirement
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-branches-in-your-repository/changing-the-default-branch"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository's default branch is named `main`.

    ## Reasons for this Default

    - `main` has been the name GitHub assigns to the default branch of new repositories since
      October 2020, so it is the name contributors expect and the name that tooling defaults
      assume.
    - The default branch is the branch checked out by a clone, the base branch proposed for new
      pull requests, and the only branch copied when generating from a template or forking with
      **Copy the DEFAULT branch only**. A name that does not match convention makes each of
      these behave in a way contributors do not anticipate.

    ## Reasons to Override this Default

    - The organization standardizes on a different name (for example, `trunk` or `develop`).
    - The repository predates the convention and renaming it would break consumers, because
      GitHub Actions workflows do not follow renames and a published action referenced as
      `@<old-branch-name>` stops resolving.

    Note that renaming the default branch updates branch protection policies, the base branch of
    open pull requests, and draft releases, but collaborators must still update their local
    clones and raw file URLs are not redirected.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: DefaultBranchRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    acceptable_values: list[str] | None = None,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = DefaultBranchRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "value": ["main"] if acceptable_values is None else acceptable_values},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = DefaultBranchRequirement()

    assert requirement.name == "DefaultBranch"
    assert (
        requirement.description
        == "Validates the repository's default branch, the branch that is checked out on clone and used as the base branch for new pull requests."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = DefaultBranchRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type == list[str]
    assert parameters["value"].default == ["main"]


# ----------------------------------------------------------------------
def test_AcceptableDefaultBranch():
    result = _Evaluate({"default_branch": "main"})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"default_branch": "main"})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"default_branch": "master"})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_AcceptableDefaultBranchAmongMultiple():
    result = _Evaluate({"default_branch": "trunk"}, ["main", "trunk"])

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_UnacceptableDefaultBranch():
    result = _Evaluate({"default_branch": "master"})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The default branch 'master' is not in the list of acceptable default branches ('main')."
    )


# ----------------------------------------------------------------------
def test_UnacceptableDefaultBranchListsAllAcceptableValues():
    result = _Evaluate({"default_branch": "master"}, ["main", "trunk"])

    assert result.context == (
        "The default branch 'master' is not in the list of acceptable default branches ('main', 'trunk')."
    )


# ----------------------------------------------------------------------
def test_UnacceptableDefaultBranchResolution():
    result = _Evaluate({"default_branch": "master"})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Default branch** section.
        3) Click the switch icon next to the current default branch name.
        4) Select a branch whose name is one of these values: 'main'.
        5) Click the **Rename branch** button.
        6) Click the **I understand, update the default branch** button.

        The repository must already contain the branch being selected, so create and push it
        first if it does not exist.

        See [Changing the default branch]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A missing default branch produces the same resolution as an unacceptable one, since both are
# fixed by pointing the setting at an acceptable branch.
def test_NoDefaultBranchResolution():
    result = _Evaluate({}, ["main", "trunk"])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Default branch** section.
        3) Click the switch icon next to the current default branch name.
        4) Select a branch whose name is one of these values: 'main', 'trunk'.
        5) Click the **Rename branch** button.
        6) Click the **I understand, update the default branch** button.

        The repository must already contain the branch being selected, so create and push it
        first if it does not exist.

        See [Changing the default branch]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The repository url is derived from the repository under audit rather than hard-coded, so it
# points at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"default_branch": "master"}, None, "https://github.example.com/o/r")

    assert result.resolution is not None
    assert "(https://github.example.com/o/r/settings)" in result.resolution


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "response",
    [
        {},
        {"default_branch": None},
    ],
)
def test_NoDefaultBranch(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "No default branch value was set."


# ----------------------------------------------------------------------
def test_EmptyAcceptableValues():
    result = _Evaluate({"default_branch": "main"}, [])

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The default branch 'main' is not in the list of acceptable default branches ()."
    )


# ----------------------------------------------------------------------
# Branch names are case sensitive in Git, so a name differing only in case is not acceptable.
def test_CaseSensitive():
    result = _Evaluate({"default_branch": "Main"})

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
def test_Skip():
    requirement = DefaultBranchRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "value": ["main"]})

    assert result.result == EvaluateResultValue.Skipped
