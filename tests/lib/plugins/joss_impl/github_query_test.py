from datetime import datetime, UTC

import pytest
import requests

from RepoAuditorWeb.lib.plugins.joss_impl import github_query
from RepoAuditorWeb.lib.plugins.joss_impl.github_query import GitHubQuery


# ----------------------------------------------------------------------
class _FakeSession:
    """Stands in for the GitHub session so that no network calls are made."""

    responses: dict[tuple[str, str | None], tuple[object, dict[str, str]]] = {}
    instances: list[_FakeSession] = []
    status_codes: dict[tuple[str, str | None], int] = {}

    # ----------------------------------------------------------------------
    def __init__(self, url: str, pat: str | None) -> None:
        self.url = url
        self.pat = pat
        self.requests: list[tuple[str, dict[str, object] | None]] = []
        self.is_closed = False

        _FakeSession.instances.append(self)

    # ----------------------------------------------------------------------
    def __enter__(self) -> _FakeSession:
        return self

    # ----------------------------------------------------------------------
    def __exit__(self, *args) -> None:
        self.is_closed = True

    # ----------------------------------------------------------------------
    def get(self, url: str, params: dict[str, object] | None = None) -> requests.Response:
        self.requests.append((url, params))

        key = (url, None if params is None else str(params.get("page")))
        payload, links = _FakeSession.responses[key]

        response = requests.Response()
        response.status_code = _FakeSession.status_codes.get(key, 200)
        response.json = lambda: payload  # ty: ignore[invalid-assignment]
        response.headers["Link"] = ", ".join(f'<{link}>; rel="{rel}"' for rel, link in links.items())

        return response


# ----------------------------------------------------------------------
@pytest.fixture
def session(monkeypatch):
    _FakeSession.instances = []
    _FakeSession.status_codes = {}
    _FakeSession.responses = {
        ("", None): ({"default_branch": "trunk", "private": False}, {}),
        ("commits", "None"): ([{"commit": {"author": {"date": "2026-01-02T03:04:05Z"}}}], {}),
        (
            "contributors",
            "1",
        ): (
            [{"login": "one", "type": "User"}, {"login": "dependabot[bot]", "type": "Bot"}, {"login": "two"}],
            {},
        ),
    }

    monkeypatch.setattr(github_query, "GitHubSession", _FakeSession)

    return _FakeSession


# ----------------------------------------------------------------------
def _GetQueryData(branch: str | None = None) -> dict[str, object]:
    query_data = GitHubQuery().GetQueryData(
        {"url": "https://github.com/owner/repo", "pat": "pat", "branch": branch}
    )
    assert query_data is not None

    return query_data


# ----------------------------------------------------------------------
def test_Construct():
    query = GitHubQuery()

    assert query.name == "GitHub"
    assert [requirement.name for requirement in query.requirements] == [
        "License",
        "PublicHistory",
        "DevelopmentHistory",
        "Contributors",
        "Issues",
    ]


# ----------------------------------------------------------------------
def test_SinglePageOfCommits(session):
    query_data = _GetQueryData()

    assert session.instances[0].url == "https://github.com/owner/repo"
    assert session.instances[0].pat == "pat"
    assert session.instances[0].requests == [
        ("", None),
        ("commits", {"sha": "trunk", "per_page": 1}),
        ("contributors", {"per_page": 100, "page": 1}),
    ]

    assert session.instances[0].is_closed is True
    assert "session" not in query_data
    assert query_data["repository"] == {"default_branch": "trunk", "private": False}
    assert query_data["first_commit_date"] == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert query_data["contributors"] == ["one", "two"]


# ----------------------------------------------------------------------
_MULTIPLE_PAGES_REQUESTS = [
    ("", None),
    ("commits", {"sha": "develop", "per_page": 1}),
    ("commits", {"sha": "develop", "per_page": 1, "page": "42"}),
    ("contributors", {"per_page": 100, "page": 1}),
    ("contributors", {"per_page": 100, "page": 2}),
]


# ----------------------------------------------------------------------
@pytest.fixture
def multiple_pages_session(session):
    session.responses[("commits", "None")] = (
        [{"commit": {"author": {"date": "2026-05-01T00:00:00Z"}}}],
        {
            "next": "https://api.github.com/commits?page=2",
            "last": "https://api.github.com/commits?per_page=1&page=42",
        },
    )
    session.responses[("commits", "42")] = ([{"commit": {"author": {"date": "2020-01-01T00:00:00Z"}}}], {})
    session.responses[("contributors", "1")] = (
        [{"login": "one"}],
        {"next": "https://api.github.com/contributors?page=2"},
    )
    session.responses[("contributors", "2")] = ([{"login": "two"}], {})

    return session


# ----------------------------------------------------------------------
def test_MultiplePages(multiple_pages_session):
    query_data = _GetQueryData("develop")

    assert multiple_pages_session.instances[0].requests == _MULTIPLE_PAGES_REQUESTS

    assert query_data["first_commit_date"] == datetime(2020, 1, 1, tzinfo=UTC)
    assert query_data["contributors"] == ["one", "two"]


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("failing_request", "num_requests"),
    [
        (("", None), 1),
        (("commits", "None"), 2),
        (("commits", "42"), 3),
        (("contributors", "1"), 4),
        (("contributors", "2"), 5),
    ],
)
def test_ErrorResponse(multiple_pages_session, failing_request, num_requests):
    multiple_pages_session.status_codes[failing_request] = 404

    with pytest.raises(requests.HTTPError):
        _GetQueryData("develop")

    assert multiple_pages_session.instances[0].requests == _MULTIPLE_PAGES_REQUESTS[:num_requests]
    assert multiple_pages_session.instances[0].is_closed is True


# ----------------------------------------------------------------------
def test_CleanupQueryData():
    query_data: dict[str, object] = {"value": 1}

    GitHubQuery().CleanupQueryData(query_data)

    assert query_data == {"value": 1}
