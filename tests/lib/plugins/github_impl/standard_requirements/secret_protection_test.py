import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.secret_protection import (
    SecretProtectionRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that secret protection is enabled.

    ## Reasons for this Default

    - A credential committed to a repository is disclosed at the moment of the push, and
      stays disclosed until it is revoked. Deleting the line does not help, because the
      commit that introduced it remains reachable, which makes finding the credential the
      part of the problem worth automating.
    - The scan covers the entire git history on all branches, along with issues, pull
      requests, discussions, and wikis, so it reports credentials that predate the setting
      being turned on rather than only those pushed afterwards.
    - Detection is by partner pattern rather than by guesswork, and GitHub notifies the
      provider that issued the credential, so a leaked token is often revoked by the
      provider before the project has read the alert.
    - Enabling the setting also brings push protection for the secret types included by
      default, which blocks the commit that would have leaked the credential; the difference
      between preventing a leak and reporting one is the cost of rotating the credential.
    - Validity checks state whether a detected credential is still live, which is what
      separates an alert that requires immediate rotation from one that documents a
      credential already revoked.
    - The setting reports rather than enforces. An alert costs the project the time to read
      it, and the credential it names was already exposed, so the setting cannot make the
      repository's position worse than it was.

    ## Reasons to Override this Default

    - The repository intentionally contains strings that resemble credentials, such as test
      fixtures, documentation examples, or revoked sample keys, and the resulting alerts
      are read as noise. Excluding paths with `secret_scanning.yml` is the narrower
      alternative to disabling the setting outright.
    - The project scans with a different tool that it already acts on, and duplicating the
      alerts across two systems means neither is treated as the authoritative one.
    - The repository is private and the organization does not hold the GitHub Secret
      Protection license the setting requires there, in which case enabling it is a
      purchasing decision rather than a configuration one.

    Note that alerts are visible only to users with write access or better, so enabling the
    setting on a public repository does not disclose the location of a credential to the
    public.

    Note also that detection is limited to the supported patterns, so the setting does not
    establish that a repository is free of credentials; a password or an internal token in a
    format no provider has registered is not detected.
    """,
)


# ----------------------------------------------------------------------
def _CreateResponse(status: str) -> dict:
    return {"security_and_analysis": {"secret_scanning": {"status": status}}}


# ----------------------------------------------------------------------
def _CreateModule(requirement: SecretProtectionRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    disallow: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = SecretProtectionRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "disallow": disallow},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SecretProtectionRequirement()

    assert requirement.name == "SecretProtection"
    assert (
        requirement.description
        == "Validates whether GitHub scans the repository's history, branches, and other content for credentials and raises an alert when one is found."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SecretProtectionRequirement().GetParameters()

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
        2) Scroll to the **Secret Protection** row.
        3) Click the **Enable** button.
        4) Confirm the change when prompted.
        5) Click the **Save changes** button at the bottom of the page.

        See [Enabling secret scanning for your repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to disable the setting when secret protection must not be enabled.
def test_ErrorResolutionWhenDisallowed():
    result = _Evaluate(_CreateResponse("enabled"), disallow=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Advanced Security settings](https://github.com/gt-csse/RepoAuditorWeb/settings/security_analysis) page.
        2) Scroll to the **Secret Protection** row.
        3) Click the **Disable** button.
        4) Confirm the change when prompted.
        5) Click the **Save changes** button at the bottom of the page.

        See [Enabling secret scanning for your repository]({_DOCUMENTATION_URL})
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
# The other secret scanning settings are distinct from the one under audit, so a response that
# reports only those is treated as though the value is not visible.
def test_UnrelatedSecretScanningSettingsAreNotUsed():
    result = _Evaluate(
        {"security_and_analysis": {"secret_scanning_push_protection": {"status": "enabled"}}},
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's security and analysis settings are not visible because the Personal Access Token provided does not grant admin access to the repository."
    )


# ----------------------------------------------------------------------
def test_Skip():
    requirement = SecretProtectionRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "disallow": False})

    assert result.result == EvaluateResultValue.Skipped
