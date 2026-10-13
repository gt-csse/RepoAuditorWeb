import re

import pytest
import requests

from RepoAuditorWeb.lib.plugins.shared.github_session import (
    GetApiBaseUrl,
    GitHubApiSession,
    GitHubSession,
)


# ----------------------------------------------------------------------
class TestGetApiBaseUrl:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("netloc", ["github.com", "www.github.com", "GitHub.com"])
    def test_Public(self, netloc):
        assert GetApiBaseUrl("https", netloc) == "https://api.github.com"

    # ----------------------------------------------------------------------
    def test_PublicIgnoresScheme(self):
        assert GetApiBaseUrl("http", "github.com") == "https://api.github.com"

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("scheme", ["https", "http"])
    def test_EnterprisePreservesScheme(self, scheme):
        assert GetApiBaseUrl(scheme, "github.mycompany.com") == f"{scheme}://github.mycompany.com/api/v3"


# ----------------------------------------------------------------------
class TestGitHubApiSession:
    # ----------------------------------------------------------------------
    def test_Attributes(self):
        session = GitHubApiSession("https://api.github.com/orgs/gt-csse", None)

        assert session.api_url == "https://api.github.com/orgs/gt-csse"
        assert session.github_pat is None
        assert session.has_pat is False
        assert session.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert session.headers["Accept"] == "application/vnd.github+json"
        assert "Authorization" not in session.headers

    # ----------------------------------------------------------------------
    def test_Pat(self):
        session = GitHubApiSession("https://api.github.com", "my_token")

        assert session.api_url == "https://api.github.com"
        assert session.github_pat == "my_token"
        assert session.has_pat is True
        assert session.headers["Authorization"] == "Bearer my_token"

    # ----------------------------------------------------------------------
    # The PAT is never sent over an unencrypted connection.
    @pytest.mark.parametrize("scheme", ["http", "file"])
    def test_PatUsesHttps(self, scheme):
        session = GitHubApiSession(f"{scheme}://github.mycompany.com/api/v3", "my_token")

        assert session.api_url == "https://github.mycompany.com/api/v3"

    # ----------------------------------------------------------------------
    def test_HttpWithoutPat(self):
        session = GitHubApiSession("http://github.mycompany.com/api/v3", None)

        assert session.api_url == "http://github.mycompany.com/api/v3"

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("api_url", ["https://api.github.com/", "https://api.github.com//"])
    def test_TrailingSlashesAreRemoved(self, api_url):
        session = GitHubApiSession(api_url, None)

        assert session.api_url == "https://api.github.com"

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("api_url", "pat"),
        [
            ("", None),
            ("", "my_token"),
            ("https://", None),
            ("http:///api/v3", "my_token"),
            ("file://github.mycompany.com/api/v3", None),
            ("github.com/api/v3", "my_token"),
            ("https://github.mycompany.com/api/v3?page=1", None),
            ("https://github.mycompany.com/api/v3#top", None),
            ("https://github.mycompany.com/api/v3;type=a", None),
            ("https://github.mycompany.com/api/v3?/", None),
            ("https://github.mycompany.com/api/v3/#/", None),
        ],
    )
    def test_ErrorInvalidApiUrl(self, api_url, pat):
        with pytest.raises(ValueError, match=re.escape(f"'{api_url}' is not a valid GitHub API URL.")):
            GitHubApiSession(api_url, pat)

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("", "https://api.github.com/orgs/gt-csse"),
            ("/repos", "https://api.github.com/orgs/gt-csse/repos"),
            ("repos", "https://api.github.com/orgs/gt-csse/repos"),
        ],
    )
    def test_UrlIsRelativeToApiUrl(self, url, expected, monkeypatch):
        requested: list[tuple[str, object]] = []

        def Request(self, method, url, *args, **kwargs):  # noqa: ARG001
            requested.append((url, kwargs["timeout"]))
            return requests.Response()

        monkeypatch.setattr(requests.Session, "request", Request)

        GitHubApiSession("https://api.github.com/orgs/gt-csse", None).get(url)

        assert requested == [(expected, 30)]

    # ----------------------------------------------------------------------
    def test_Retries(self):
        adapter = GitHubApiSession("https://api.github.com", None).get_adapter("https://api.github.com")
        retries = adapter.max_retries  # ty: ignore[unresolved-attribute]

        assert retries.total == 3
        assert retries.backoff_factor == 1
        assert retries.status_forcelist == [429, 500, 502, 503, 504]


# ----------------------------------------------------------------------
class TestGitHubSession:
    # ----------------------------------------------------------------------
    # These urls are rejected before reaching GitHubSession when supplied on the command line, but
    # GitHubSession is public and validates them itself.
    @pytest.mark.parametrize(
        ("url", "pat"),
        [
            ("https:///gt-csse/RepoAuditorWeb", None),
            ("ftp://github.mycompany.com/gt-csse/RepoAuditorWeb", "my_token"),
            ("//github.mycompany.com/gt-csse/RepoAuditorWeb", "my_token"),
        ],
    )
    def test_ErrorInvalidUrl(self, url, pat):
        with pytest.raises(ValueError, match=re.escape(f"'{url}' is not a valid GitHub repository URL.")):
            GitHubSession(url, pat)
