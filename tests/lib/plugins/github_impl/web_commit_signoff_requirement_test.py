import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.web_commit_signoff_requirement import (
    WebCommitSignoffRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to not require contributors to sign off on web-based commits. When
    the requirement is enabled, GitHub's web interface tells the contributor that committing
    also constitutes signing off, and appends a `Signed-off-by` trailer on their behalf.

    ## Reasons for this Default

    - The project has no signoff policy, in which case the trailer asserts a certification
      (commonly the [Developer Certificate of Origin](https://developercertificate.org/)) that
      the project does not actually require.
    - The project wants signing off to be a separate, deliberate act rather than a side effect
      of committing, because the trailer certifies that the contributor holds the rights to
      submit the change and the record is retained indefinitely.

    ## Reasons to Override this Default

    - Projects that enforce a signoff policy typically verify it with a status check that fails
      when a trailer is missing. Contributors editing through the web interface cannot pass
      `--signoff`, so the check fails after the fact and recovering from it requires rewriting
      history.
    - The trailer is the same one produced by `git commit --signoff`, so requiring it makes
      web-based commits consistent with signed-off commits made from the command line.

    Note that this requirement governs only the web interface; commits made from the command
    line are unaffected, so it does not by itself guarantee that every commit is signed off.
    """,
)


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features"
    "/managing-repository-settings/managing-the-commit-signoff-policy-for-your-repository"
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: WebCommitSignoffRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    enforce: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = WebCommitSignoffRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "enforce": enforce},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = WebCommitSignoffRequirement()

    assert requirement.name == "WebCommitSignoff"
    assert (
        requirement.description
        == "Validates whether contributors must sign off on commits made through GitHub's web interface; commits made from the command line are unaffected."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = WebCommitSignoffRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "enforce"]
    assert parameters["enforce"].type is bool
    assert parameters["enforce"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("web_commit_signoff_required", "enforce"),
    [(False, False), (True, True)],
)
def test_MatchingValue(web_commit_signoff_required, enforce):
    result = _Evaluate(
        {"web_commit_signoff_required": web_commit_signoff_required},
        enforce=enforce,
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"web_commit_signoff_required": False})

    assert result.resolution is None
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolutionAndRationale():
    result = _Evaluate({"web_commit_signoff_required": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Commits** section.
        3) Uncheck the **Require contributors to sign off on web-based commits** checkbox.

        See [Managing the commit signoff policy for your repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when signoff is enforced.
def test_ErrorResolutionWhenEnforced():
    result = _Evaluate({"web_commit_signoff_required": False}, enforce=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Commits** section.
        3) Check the **Require contributors to sign off on web-based commits** checkbox.

        See [Managing the commit signoff policy for your repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
def test_SignoffNotEnabledWhenEnforced():
    result = _Evaluate({"web_commit_signoff_required": False}, enforce=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_SignoffEnabledWhenNotEnforced():
    result = _Evaluate({"web_commit_signoff_required": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An absent key is treated as False, so it satisfies a requirement of False.
def test_MissingValue():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_MissingValueWhenEnforced():
    result = _Evaluate({}, enforce=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_Skip():
    requirement = WebCommitSignoffRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "enforce": False})

    assert result.result == EvaluateResultValue.Skipped


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        {"web_commit_signoff_required": True},
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution
