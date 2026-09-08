import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.restricted_value import (
    AccessLevel,
    GetRestrictedValue,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _Invoke(
    response: dict,
    *,
    keys: str | tuple[str, ...] = "allow_merge_commit",
    value_description: str = "merge settings",
    pat: str | None = "my-pat",
    access_level: AccessLevel = AccessLevel.Push,
) -> EvaluateResult | object:
    requirement = MyRequirement("MyRequirement", "My description.")
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])

    return GetRestrictedValue(
        module,
        requirement,
        {
            "response": response,
            "session": GitHubSession("https://github.com/gt-csse/RepoAuditorWeb", pat),
        },
        keys,
        value_description,
        access_level,
    )


# ----------------------------------------------------------------------
# A visible value is returned as itself so that the caller evaluates it directly.
@pytest.mark.parametrize("value", [True, False])
def test_VisibleValue(value):
    assert _Invoke({"allow_merge_commit": value}) is value


# ----------------------------------------------------------------------
# The key is a parameter so that any restricted setting can be read, not just the merge methods.
def test_ReadsTheRequestedKey():
    assert _Invoke({"delete_branch_on_merge": True}, keys="delete_branch_on_merge") is True


# ----------------------------------------------------------------------
# Some settings are nested within the response, so a sequence of keys describes the path to them.
def test_ReadsNestedKeys():
    response = {"security_and_analysis": {"dependabot_security_updates": {"status": "enabled"}}}

    value = _Invoke(
        response,
        keys=("security_and_analysis", "dependabot_security_updates", "status"),
    )

    assert value == "enabled"


# ----------------------------------------------------------------------
# A path that stops short is not visible, so it is reported rather than raising.
@pytest.mark.parametrize(
    "response",
    [
        {},
        {"security_and_analysis": None},
        {"security_and_analysis": {}},
        {"security_and_analysis": {"dependabot_security_updates": {}}},
    ],
)
def test_NestedKeysNotVisible(response):
    result = _Invoke(
        response,
        keys=("security_and_analysis", "dependabot_security_updates", "status"),
    )

    assert isinstance(result, EvaluateResult)
    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
# A value along the path that is not a dictionary cannot be traversed further.
def test_NestedKeysStopAtNonDictionary():
    result = _Invoke({"security_and_analysis": True}, keys=("security_and_analysis", "status"))

    assert isinstance(result, EvaluateResult)
    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
# The access level is interpolated because GitHub restricts different settings to different levels.
def test_AdminAccessLevelContext():
    result = _Invoke({}, value_description="security and analysis settings", access_level=AccessLevel.Admin)

    assert isinstance(result, EvaluateResult)
    assert result.context == (
        "The repository's security and analysis settings are not visible because the Personal Access Token provided does not grant admin access to the repository."
    )


# ----------------------------------------------------------------------
def test_AdminAccessLevelResolutionWithoutPat():
    result = _Invoke({}, pat=None, access_level=AccessLevel.Admin)

    assert isinstance(result, EvaluateResult)
    assert result.resolution == textwrap.dedent(
        """\
        1) Create a [Personal Access Token](https://github.com/settings/personal-access-tokens)
           with admin access to the repository.
        2) Provide it via the `--GitHub-pat` command line argument or the
           `REPO_AUDITOR_WEB_GITHUB_PAT` environment variable.

        See [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
        for more information.
        """,
    )


# ----------------------------------------------------------------------
def test_AdminAccessLevelResolutionWithPat():
    result = _Invoke({}, access_level=AccessLevel.Admin)

    assert isinstance(result, EvaluateResult)
    assert result.resolution == textwrap.dedent(
        """\
        1) Open the [Personal Access Tokens](https://github.com/settings/personal-access-tokens) page.
        2) Grant the token admin access to the repository, or replace it with one that has it. A
           fine-grained token must also list the repository among those it can access.

        See [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# Without a token the omission is the user's to correct, so it warns rather than failing.
def test_NotVisibleWithoutPat():
    result = _Invoke({}, pat=None)

    assert isinstance(result, EvaluateResult)
    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's merge settings are not visible because a Personal Access Token was not provided."
    )


# ----------------------------------------------------------------------
def test_NotVisibleWithoutPatResolution():
    result = _Invoke({}, pat=None)

    assert isinstance(result, EvaluateResult)
    assert result.resolution == textwrap.dedent(
        """\
        1) Create a [Personal Access Token](https://github.com/settings/personal-access-tokens)
           with push access to the repository.
        2) Provide it via the `--GitHub-pat` command line argument or the
           `REPO_AUDITOR_WEB_GITHUB_PAT` environment variable.

        See [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A token that cannot see the setting is a misconfiguration of the token, so it is an error rather
# than a warning.
def test_NotVisibleWithPat():
    result = _Invoke({})

    assert isinstance(result, EvaluateResult)
    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's merge settings are not visible because the Personal Access Token provided does not grant push access to the repository."
    )


# ----------------------------------------------------------------------
def test_NotVisibleWithPatResolution():
    result = _Invoke({})

    assert isinstance(result, EvaluateResult)
    assert result.resolution == textwrap.dedent(
        """\
        1) Open the [Personal Access Tokens](https://github.com/settings/personal-access-tokens) page.
        2) Grant the token push access to the repository, or replace it with one that has it. A
           fine-grained token must also list the repository among those it can access.

        See [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The description is interpolated so that each requirement names the settings it reads.
@pytest.mark.parametrize("pat", [None, "my-pat"])
def test_ValueDescriptionIsUsed(pat):
    result = _Invoke({}, value_description="automatic merge settings", pat=pat)

    assert isinstance(result, EvaluateResult)
    assert result.context is not None
    assert result.context.startswith("The repository's automatic merge settings are not visible")


# ----------------------------------------------------------------------
# A rationale would explain a default that could not be evaluated, so it is omitted; the problem is
# the token rather than the repository's configuration.
@pytest.mark.parametrize("pat", [None, "my-pat"])
def test_NoRationale(pat):
    result = _Invoke({}, pat=pat)

    assert isinstance(result, EvaluateResult)
    assert result.rationale is None


# ----------------------------------------------------------------------
def test_RequirementAndModuleAreCarried():
    requirement = MyRequirement("MyRequirement", "My description.")
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])

    result = GetRestrictedValue(
        module,
        requirement,
        {
            "response": {},
            "session": GitHubSession("https://github.com/gt-csse/RepoAuditorWeb", None),
        },
        "allow_merge_commit",
        "merge settings",
    )

    assert isinstance(result, EvaluateResult)
    assert result.requirement is requirement
    assert result.module is module
