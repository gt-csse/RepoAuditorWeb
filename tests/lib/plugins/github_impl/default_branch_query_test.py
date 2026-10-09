from RepoAuditorWeb.lib.plugins.github_impl.default_branch_query import DefaultBranchQuery

from conftest import FakeGitHubSession


# ----------------------------------------------------------------------
# Characters that git permits in a branch name must not end the path.
def test_BranchIsEncoded():
    session = FakeGitHubSession(
        {
            "": (200, {"default_branch": "my#branch"}),
            "branches/my%23branch": (200, {"protected": True}),
        },
    )

    query_data = DefaultBranchQuery().GetQueryData({"session": session})

    assert query_data is not None
    assert query_data["default_branch"] == "my#branch"
    assert query_data["response"] == {"protected": True}
    assert session.requested_urls == ["", "branches/my%23branch"]
