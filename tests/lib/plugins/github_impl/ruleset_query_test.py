import pytest
import requests

from RepoAuditorWeb.lib.plugins.github_impl.ruleset_query import RulesetQuery

from conftest import FakeGitHubSession


# ----------------------------------------------------------------------
# Characters that git permits in a branch name must not end the path.
def test_BranchIsEncoded():
    session = FakeGitHubSession(
        {
            "": (200, {"default_branch": "main", "owner": {"type": "Organization"}}),
            "rules/branches/my%23branch": (200, [{"type": "deletion"}]),
        },
    )

    query_data = RulesetQuery().GetQueryData({"session": session, "branch": "my#branch"})

    assert query_data is not None
    assert query_data["branch"] == "my#branch"
    assert query_data["response"] == [{"type": "deletion"}]
    assert query_data["owner_type"] == "Organization"
    assert session.requested_urls == ["", "rules/branches/my%23branch"]


# ----------------------------------------------------------------------
def test_DefaultBranch():
    session = FakeGitHubSession(
        {
            "": (200, {"default_branch": "trunk", "owner": {"type": "User"}}),
            "rules/branches/trunk": (200, [{"type": "deletion"}]),
        },
    )

    query_data = RulesetQuery().GetQueryData({"session": session, "branch": None})

    assert query_data is not None
    assert query_data["branch"] == "trunk"
    assert query_data["owner_type"] == "User"
    assert session.requested_urls == ["", "rules/branches/trunk"]


# ----------------------------------------------------------------------
def test_NoRulesets():
    session = FakeGitHubSession(
        {
            "": (200, {"default_branch": "main", "owner": {"type": "Organization"}}),
            "rules/branches/main": (200, []),
        },
    )

    assert RulesetQuery().GetQueryData({"session": session, "branch": "main"}) is None


# ----------------------------------------------------------------------
# The repository is fetched even when the branch is supplied, so its failure must not be masked.
def test_RepositoryErrorResponseStatus():
    session = FakeGitHubSession({"": (404, {})})

    with pytest.raises(requests.HTTPError):
        RulesetQuery().GetQueryData({"session": session, "branch": "main"})

    assert session.requested_urls == [""]


# ----------------------------------------------------------------------
def test_RulesErrorResponseStatus():
    session = FakeGitHubSession(
        {
            "": (200, {"default_branch": "main", "owner": {"type": "Organization"}}),
            "rules/branches/main": (404, {}),
        },
    )

    with pytest.raises(requests.HTTPError):
        RulesetQuery().GetQueryData({"session": session, "branch": "main"})
