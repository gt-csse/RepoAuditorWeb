from RepoAuditorWeb.lib.plugins.github_impl.ruleset_query import RulesetQuery

from conftest import FakeGitHubSession


# ----------------------------------------------------------------------
# Characters that git permits in a branch name must not end the path.
def test_BranchIsEncoded():
    session = FakeGitHubSession({"rules/branches/my%23branch": (200, [{"type": "deletion"}])})

    query_data = RulesetQuery().GetQueryData({"session": session, "branch": "my#branch"})

    assert query_data is not None
    assert query_data["branch"] == "my#branch"
    assert query_data["response"] == [{"type": "deletion"}]
    assert session.requested_urls == ["rules/branches/my%23branch"]
