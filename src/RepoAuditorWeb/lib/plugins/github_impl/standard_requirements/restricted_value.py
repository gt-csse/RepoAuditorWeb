"""Functionality for reading repository values that GitHub only reports to privileged callers."""

import textwrap

from enum import StrEnum
from typing import cast, TYPE_CHECKING

from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Markdown, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
# Sentence fragment naming the settings a requirement reads, used to describe what is not visible.
type ValueDescription = str


# ----------------------------------------------------------------------
# GitHub reports the 'security_and_analysis' settings as objects rather than booleans so that
# additional state can be introduced without changing the shape of the response.
ENABLED_STATUS = "enabled"


# ----------------------------------------------------------------------
class AccessLevel(StrEnum):
    """Repository access a Personal Access Token must grant for a restricted value to be visible."""

    Push = "push"
    Admin = "admin"


# ----------------------------------------------------------------------
def GetRestrictedValue(
    module: Module,
    requirement: Requirement,
    query_data: dict[str, object],
    keys: str | tuple[str, ...],
    value_description: ValueDescription,
    access_level: AccessLevel = AccessLevel.Push,
) -> EvaluateResult | object:
    """Return the response value at 'keys', or an EvaluateResult explaining why it is not visible.

    GitHub omits administrative settings for callers without sufficient access, so an absent key
    means the value is unknown rather than False and must not be evaluated as one. Callers must
    return the value returned by this function immediately if it is an EvaluateResult.
    """

    value: object = cast(dict, query_data["response"])

    for key in (keys,) if isinstance(keys, str) else keys:
        if not isinstance(value, dict):
            value = None
            break

        value = value.get(key)

    if value is not None:
        return value

    # The rationale is omitted because it explains a default that could not be evaluated; the
    # problem is the token rather than the repository's configuration.
    #
    # A token that cannot see the value is a misconfiguration of the token, which is an error the
    # user must fix for the requirement to mean anything. Providing no token at all is a warning
    # instead, since running without one is a legitimate way to audit what is publicly visible.
    if cast("GitHubSession", query_data["session"]).has_pat:
        return EvaluateResult(
            EvaluateResultValue.Error,
            f"The repository's {value_description} are not visible because the Personal Access Token provided does not grant {access_level} access to the repository.",
            _CreateInsufficientPatResolution(access_level),
            None,
            requirement,
            module,
        )

    return EvaluateResult(
        EvaluateResultValue.Warning,
        f"The repository's {value_description} are not visible because a Personal Access Token was not provided.",
        _CreateNoPatResolution(access_level),
        None,
        requirement,
        module,
    )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _CreateNoPatResolution(access_level: AccessLevel) -> Markdown:
    return textwrap.dedent(
        f"""\
        1) Create a [Personal Access Token](https://github.com/settings/personal-access-tokens)
           with {access_level} access to the repository.
        2) Provide it via the `--GitHub-pat` command line argument or the
           `REPO_AUDITOR_WEB_GITHUB_PAT` environment variable.

        See [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
        for more information.
        """,
    )


# ----------------------------------------------------------------------
def _CreateInsufficientPatResolution(access_level: AccessLevel) -> Markdown:
    return textwrap.dedent(
        f"""\
        1) Open the [Personal Access Tokens](https://github.com/settings/personal-access-tokens) page.
        2) Grant the token {access_level} access to the repository, or replace it with one that has it. A
           fine-grained token must also list the repository among those it can access.

        See [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
        for more information.
        """,
    )
