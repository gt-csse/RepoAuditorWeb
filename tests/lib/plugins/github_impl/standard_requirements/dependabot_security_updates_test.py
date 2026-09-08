import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.dependabot_security_updates import (
    DependabotSecurityUpdatesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that Dependabot security updates are enabled.

    Note that this differs from the state of a newly created repository, where the setting is
    disabled.

    ## Reasons for this Default

    - A dependency with a published advisory is a vulnerability the project already has, and
      the patched version already exists. What remains is the work of noticing the advisory
      and applying the update, which is what this setting performs.
    - An alert states that a problem exists; a pull request states what to do about it. The
      difference matters because the alert is read by whoever thinks to look at the security
      tab, while the pull request arrives where the project already reviews changes.
    - Advisories are published on the ecosystem's schedule rather than the project's, so a
      project that updates dependencies only when it happens to touch them is exposed for
      however long it is between such occasions. Automating the response removes that
      interval.
    - The change is proposed rather than applied. It arrives as a pull request against the
      default branch, subject to the same review and status checks as any other change, so
      enabling the setting delegates the noticing rather than the deciding.
    - The update is the smallest one that resolves the advisory, so the pull request is
      usually a version bump rather than a migration, and the cost of reviewing it is
      correspondingly small.

    ## Reasons to Override this Default

    - The project prefers to choose which alerts produce pull requests. Dependabot attempts
      to open one for every open alert that has a patch available, which on a large or
      long-neglected dependency set is a volume of pull requests that is read as noise and
      then ignored. Auto-triage rules, applied with the setting disabled, are the documented
      alternative.
    - Pull requests trigger workflows, so on a project with expensive continuous integration
      the automated updates consume Actions minutes on a schedule the project does not
      control.
    - Dependencies are managed outside the repository, such as by a vendored tree, an
      internal mirror, or a tool that resolves versions centrally, in which case a pull
      request that edits a manifest proposes a change the project cannot merge.

    Note that the setting depends on the dependency graph and Dependabot alerts; enabling
    Dependabot enables the dependency graph if it is not already on.

    Note also that updates are raised against the default branch only, and only for
    dependencies declared in a manifest or lock file, so a repository whose dependencies are
    detected but not declared receives alerts without corresponding pull requests. Not every
    ecosystem supports security updates, and a repository with no manifest has nothing for
    the setting to act on.
    """,
)


# ----------------------------------------------------------------------
def _CreateResponse(status: str) -> dict:
    return {"security_and_analysis": {"dependabot_security_updates": {"status": status}}}


# ----------------------------------------------------------------------
def _CreateModule(requirement: DependabotSecurityUpdatesRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = DependabotSecurityUpdatesRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = DependabotSecurityUpdatesRequirement()

    assert requirement.name == "DependabotSecurityUpdates"
    assert (
        requirement.description
        == "Validates whether Dependabot automatically opens pull requests that update dependencies with known vulnerabilities to a patched version."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = DependabotSecurityUpdatesRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "disallow"]
    assert parameters["disallow"].type is bool
    assert parameters["disallow"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("status", "disallow"),
    [("enabled", False), ("disabled", True)],
)
def test_MatchingStatus(status, disallow):
    result = _Evaluate(_CreateResponse(status), disallow=disallow)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate(_CreateResponse("enabled"))

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate(_CreateResponse("disabled"))

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate(_CreateResponse("disabled"))

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Advanced Security settings](https://github.com/gt-csse/RepoAuditorWeb/settings/security_analysis) page.
        2) Scroll to the **Dependabot security updates** row.
        3) Click the **Enable** button.
        4) Click the **Save changes** button.

        See [Configuring Dependabot security updates]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to disable the setting when the updates must not be enabled.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate(_CreateResponse("enabled"), disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Advanced Security settings](https://github.com/gt-csse/RepoAuditorWeb/settings/security_analysis) page.
        2) Scroll to the **Dependabot security updates** row.
        3) Click the **Disable** button.
        4) Click the **Save changes** button.

        See [Configuring Dependabot security updates]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        _CreateResponse("disabled"),
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/security_analysis)" in result.resolution


# ----------------------------------------------------------------------
def test_DisabledWhenRequired():
    result = _Evaluate(_CreateResponse("disabled"))

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_EnabledWhenDisallowed():
    result = _Evaluate(_CreateResponse("enabled"), disallow=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# An explicit 'disabled' is a visible setting that is genuinely off, so it fails rather than being
# treated as the unknown case.
def test_DisabledIsDistinctFromUnknown():
    result = _Evaluate(_CreateResponse("disabled"), pat=None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# GitHub omits the security and analysis settings for a caller without admin access, so an absent
# value means the setting is unknown rather than disabled. A missing token is the user's to
# correct, so it warns.
@pytest.mark.parametrize(
    "response",
    [
        {},
        {"security_and_analysis": None},
        {"security_and_analysis": {}},
    ],
)
def test_MissingStatusWithoutPat(response):
    result = _Evaluate(response, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's security and analysis settings are not visible because a Personal Access Token was not provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingStatusWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# The setting requires admin access rather than the push access that the other restricted settings
# require, so the resolution asks for admin access.
def test_MissingStatusWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's security and analysis settings are not visible because the Personal Access Token provided does not grant admin access to the repository."
    )


# ----------------------------------------------------------------------
# The setting cannot be evaluated when it is not visible, so 'disallow' does not turn an unknown
# value into a passing result.
@pytest.mark.parametrize(
    ("pat", "expected_result"),
    [
        (None, EvaluateResultValue.Warning),
        ("my-pat", EvaluateResultValue.Error),
    ],
)
def test_MissingStatusWhenDisallowed(pat, expected_result):
    result = _Evaluate({}, disallow=True, pat=pat)

    assert result.result == expected_result


# ----------------------------------------------------------------------
# The rationale explains a default that could not be evaluated, so it is omitted when the setting is
# not visible; the problem is the token rather than the repository's configuration.
@pytest.mark.parametrize("pat", [None, "my-pat"])
def test_MissingStatusHasNoRationale(pat):
    result = _Evaluate({}, pat=pat)

    assert result.rationale is None


# ----------------------------------------------------------------------
def test_Skip():
    requirement = DependabotSecurityUpdatesRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
