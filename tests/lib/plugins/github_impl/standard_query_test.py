import pytest
import requests

from RepoAuditorWeb.lib.plugins.github_impl.standard_query import StandardQuery


# ----------------------------------------------------------------------
class _FakeSession:
    """Stands in for the GitHub session so that no network calls are made."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        payload: object = None,
        status_code: int = 200,
    ) -> None:
        self.payload = payload
        self.status_code = status_code
        self.requested_url: str | None = None

    # ----------------------------------------------------------------------
    def get(self, url: str) -> requests.Response:
        self.requested_url = url

        response = requests.Response()
        response.status_code = self.status_code
        response.url = "https://api.github.com/repos/username/repo"
        response.json = lambda: self.payload  # ty: ignore[invalid-assignment]

        return response


# ----------------------------------------------------------------------
def test_Construct():
    query = StandardQuery()

    assert query.name == "Standard"
    assert [requirement.name for requirement in query.requirements] == [
        "Description",
        "License",
        "Template",
        "WebCommitSignoff",
        "DefaultBranch",
        "SupportWikis",
        "SupportIssues",
        "SupportDiscussions",
        "SupportProjects",
        "SupportPullRequests",
        "MergeCommit",
        "MergeCommitMessage",
        "SquashCommit",
        "SquashCommitMessage",
        "RebaseCommit",
        "SuggestUpdatingPullRequestBranches",
        "AutoMerge",
        "DeleteBranchOnMerge",
    ]


# ----------------------------------------------------------------------
def test_GetQueryData():
    payload = {"description": "My description."}
    session = _FakeSession(payload)

    query_data = StandardQuery().GetQueryData({"session": session})

    assert query_data is not None
    assert query_data["response"] is payload


# ----------------------------------------------------------------------
# The repository endpoint is the session's base url, so an empty relative url is requested.
def test_RequestsTheRepositoryEndpoint():
    session = _FakeSession({})

    StandardQuery().GetQueryData({"session": session})

    assert session.requested_url == ""


# ----------------------------------------------------------------------
# The module data is augmented in place rather than replaced, so existing values are preserved.
def test_PreservesModuleData():
    session = _FakeSession({})
    module_data: dict[str, object] = {"session": session}

    query_data = StandardQuery().GetQueryData(module_data)

    assert query_data is module_data
    assert query_data["session"] is session


# ----------------------------------------------------------------------
# The branch supplied by the module is passed through untouched for requirements to consume.
def test_PreservesBranch():
    query_data = StandardQuery().GetQueryData({"session": _FakeSession({}), "branch": "main"})

    assert query_data is not None
    assert query_data["branch"] == "main"


# ----------------------------------------------------------------------
def test_ErrorResponseStatus():
    with pytest.raises(requests.HTTPError):
        StandardQuery().GetQueryData({"session": _FakeSession({}, status_code=404)})
