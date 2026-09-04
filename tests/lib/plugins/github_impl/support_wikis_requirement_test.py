import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.support_wikis_requirement import SupportWikisRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/communities/documenting-your-project-with-wikis/disabling-wikis"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository's wiki is disabled, which matches
    the state of a newly created repository.

    ## Reasons for this Default

    - Wiki content is stored in a separate git repository (`<repository>.wiki.git`) rather than
      alongside the code, so it is not part of any commit, branch, tag, or release. A change
      cannot be reviewed with the code it documents, and documentation for a released version
      cannot be recovered by checking out that release.
    - The wiki has no pull request support, so edits land without review. Documentation kept in
      the repository is subject to the same review and status checks as the code.
    - Wiki content is not copied when the repository is forked or generated from a template, so
      contributors working from a fork lose the documentation.
    - The wiki is a distinct search surface (`type=Wikis`) and is excluded from code search, and
      search engines index only wikis belonging to repositories with 500 or more stars that
      also prevent public editing. Documentation placed there is harder to find than the same
      content in the repository.
    - Enabling the feature without populating it presents contributors with a documentation
      location that competes with the repository, which invites the two to diverge.

    ## Reasons to Override this Default

    - The project wants documentation that contributors can edit without cloning the repository
      or opening a pull request, which is the wiki's purpose.
    - The documentation is not tied to a specific version of the code (for example, meeting
      notes, a roadmap, or troubleshooting notes), so keeping it out of the repository's
      history is an advantage rather than a cost.

    Note that disabling the wiki hides existing content rather than erasing it; re-enabling the
    feature restores the previous pages. Also note that for a public repository, editing is
    restricted to collaborators by default and the wiki has a soft limit of 5,000 files.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SupportWikisRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = SupportWikisRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SupportWikisRequirement()

    assert requirement.name == "SupportWikis"
    assert (
        requirement.description
        == "Validates whether the repository's wiki is enabled; wiki content lives in a separate repository that is not versioned alongside the code."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SupportWikisRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("has_wiki", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(has_wiki, require):
    result = _Evaluate({"has_wiki": has_wiki}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"has_wiki": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"has_wiki": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"has_wiki": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Uncheck the **Wikis** checkbox.

        See [Disabling wikis]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when the wiki is required.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"has_wiki": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Check the **Wikis** checkbox.

        See [Disabling wikis]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"has_wiki": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_WikiWhenNotRequired():
    result = _Evaluate({"has_wiki": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NoWikiWhenRequired():
    result = _Evaluate({"has_wiki": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An absent 'has_wiki' key is treated as False, so it satisfies a requirement of False.
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
    requirement = SupportWikisRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
