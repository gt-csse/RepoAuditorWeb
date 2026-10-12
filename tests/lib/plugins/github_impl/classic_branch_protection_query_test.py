import pytest
import requests

from RepoAuditorWeb.lib.plugins.github_impl.classic_branch_protection_query import (
    ClassicBranchProtectionQuery,
)

from conftest import FakeGitHubSession


# ----------------------------------------------------------------------
_PROTECTION = {"url": "https://api.github.com/repos/username/repo/branches/main/protection"}


# ----------------------------------------------------------------------
def _GetQueryData(
    responses: dict[str, tuple[int, object]],
    branch: str | None = "main",
) -> tuple[dict[str, object] | None, FakeGitHubSession]:
    session = FakeGitHubSession(responses)

    return ClassicBranchProtectionQuery().GetQueryData({"session": session, "branch": branch}), session


# ----------------------------------------------------------------------
def test_ClassicProtection():
    query_data, _ = _GetQueryData(
        {
            "branches/main": (200, {"protected": True}),
            "branches/main/protection": (200, _PROTECTION),
        },
    )

    assert query_data is not None
    assert query_data["branch"] == "main"
    assert query_data["response"] == _PROTECTION


# ----------------------------------------------------------------------
def test_DefaultBranch():
    query_data, _ = _GetQueryData(
        {
            "": (200, {"default_branch": "trunk"}),
            "branches/trunk": (200, {"protected": True}),
            "branches/trunk/protection": (200, _PROTECTION),
        },
        branch=None,
    )

    assert query_data is not None
    assert query_data["branch"] == "trunk"


# ----------------------------------------------------------------------
def test_Unprotected():
    query_data, _ = _GetQueryData({"branches/main": (200, {"protected": False})})

    assert query_data is None


# ----------------------------------------------------------------------
# A protected branch without a classic rule is governed by rulesets.
def test_RulesetProtection():
    query_data, _ = _GetQueryData(
        {
            "branches/main": (200, {"protected": True}),
            "branches/main/protection": (404, {}),
            "rules/branches/main": (200, [{"type": "deletion"}]),
        },
    )

    assert query_data is None


# ----------------------------------------------------------------------
# GitHub reports classic protection only to administrators, so the requirement is given the
# opportunity to report that it is not visible rather than the audit failing.
@pytest.mark.parametrize("status_code", [401, 403])
def test_NotVisible(status_code):
    query_data, _ = _GetQueryData(
        {
            "branches/main": (200, {"protected": True}),
            "branches/main/protection": (status_code, {}),
        },
    )

    assert query_data is not None
    assert query_data["branch"] == "main"
    assert query_data["response"] is None


# ----------------------------------------------------------------------
def test_ErrorNotFoundWithoutRules():
    with pytest.raises(requests.HTTPError):
        _GetQueryData(
            {
                "branches/main": (200, {"protected": True}),
                "branches/main/protection": (404, {}),
                "rules/branches/main": (200, []),
            },
        )


# ----------------------------------------------------------------------
# Characters that git permits in a branch name must not end the path.
def test_BranchIsEncoded():
    _, session = _GetQueryData(
        {
            "branches/feature/my%23branch": (200, {"protected": True}),
            "branches/feature/my%23branch/protection": (200, _PROTECTION),
        },
        branch="feature/my#branch",
    )

    assert session.requested_urls == [
        "branches/feature/my%23branch",
        "branches/feature/my%23branch/protection",
    ]
