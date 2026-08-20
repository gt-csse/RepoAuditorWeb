import re

import pytest
import requests

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule, GitHubSession


# ----------------------------------------------------------------------
def _GetSession(
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = None,
) -> GitHubSession:
    module_data = GitHubModule().GetModuleData(
        {None: {"skip": False, "url": url, "pat": pat, "branch": None}},
    )

    assert module_data is not None
    return module_data[None]["session"]  # ty: ignore[invalid-return-type]


# ----------------------------------------------------------------------
def test_Construct():
    module = GitHubModule()

    assert module.name == "GitHub"
    assert module.description == "Validates GitHub configuration settings."
    assert [query.name for query in module.queries] == ["Standard"]
    assert module.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = GitHubModule().GetParameters()

    assert list(parameters.keys()) == ["skip", "url", "pat", "branch"]
    assert parameters["url"].type is str
    assert parameters["url"].default is None
    assert parameters["pat"].type == (str | None)
    assert parameters["branch"].type == (str | None)


# ----------------------------------------------------------------------
class TestGetModuleData:
    # ----------------------------------------------------------------------
    def test_ReplacesModuleArgumentsWithSession(self):
        module_data = GitHubModule().GetModuleData(
            {
                None: {
                    "skip": False,
                    "url": "https://github.com/gt-csse/RepoAuditorWeb",
                    "pat": None,
                    "branch": None,
                },
            },
        )

        assert module_data is not None
        assert list(module_data[None].keys()) == ["session", "branch"]

    # ----------------------------------------------------------------------
    # The branch is carried through so that queries can evaluate a non-default branch.
    @pytest.mark.parametrize("branch", [None, "main"])
    def test_BranchIsPreserved(self, branch):
        module_data = GitHubModule().GetModuleData(
            {
                None: {
                    "skip": False,
                    "url": "https://github.com/gt-csse/RepoAuditorWeb",
                    "pat": None,
                    "branch": branch,
                },
            },
        )

        assert module_data is not None
        assert module_data[None]["branch"] == branch

    # ----------------------------------------------------------------------
    def test_PreservesRequirementArguments(self):
        requirement_arguments: dict[str, object] = {"skip": False, "value": "populated"}

        module_data = GitHubModule().GetModuleData(
            {
                None: {
                    "skip": False,
                    "url": "https://github.com/gt-csse/RepoAuditorWeb",
                    "pat": None,
                    "branch": None,
                },
                "Description": requirement_arguments,
            },
        )

        assert module_data is not None
        assert module_data["Description"] is requirement_arguments

    # ----------------------------------------------------------------------
    # A skipped module is never asked for data, so the absent url is not an error.
    def test_Skip(self):
        assert GitHubModule().GetModuleData({None: {"skip": True}}) is None

    # ----------------------------------------------------------------------
    def test_ErrorMissingUrl(self):
        with pytest.raises(ValueError, match=re.escape("'url' is required argument for this module.")):
            GitHubModule().GetModuleData({None: {"skip": False, "url": None, "pat": None}})


# ----------------------------------------------------------------------
class TestSession:
    # ----------------------------------------------------------------------
    def test_Attributes(self):
        session = _GetSession()

        assert session.github_url == "https://github.com/gt-csse/RepoAuditorWeb"
        assert session.github_username == "gt-csse"
        assert session.github_repository == "RepoAuditorWeb"
        assert session.api_url == "https://api.github.com/repos/gt-csse/RepoAuditorWeb"
        assert session.is_enterprise is False
        assert session.has_pat is False
        assert session.github_pat is None

    # ----------------------------------------------------------------------
    def test_Headers(self):
        session = _GetSession()

        assert session.headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert session.headers["Accept"] == "application/vnd.github+json"
        assert "Authorization" not in session.headers

    # ----------------------------------------------------------------------
    def test_Pat(self):
        session = _GetSession(pat="my_token")

        assert session.headers["Authorization"] == "Bearer my_token"
        assert session.github_pat == "my_token"
        assert session.has_pat is True

    # ----------------------------------------------------------------------
    # A PAT that names an existing file is read from that file, so tokens need not appear on the
    # command line.
    def test_PatFromFile(self, tmp_path):
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text("  my_file_token\n", encoding="utf-8")

        session = _GetSession(pat=str(pat_filename))

        assert session.github_pat == "my_file_token"
        assert session.headers["Authorization"] == "Bearer my_file_token"

    # ----------------------------------------------------------------------
    def test_TrailingSlashIsRemoved(self):
        session = _GetSession("https://github.com/gt-csse/RepoAuditorWeb/")

        assert session.github_url == "https://github.com/gt-csse/RepoAuditorWeb"
        assert session.api_url == "https://api.github.com/repos/gt-csse/RepoAuditorWeb"

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/gt-csse/RepoAuditorWeb",
            "https://www.github.com/gt-csse/RepoAuditorWeb",
        ],
    )
    def test_PublicGitHubUrls(self, url):
        session = _GetSession(url)

        assert session.api_url == "https://api.github.com/repos/gt-csse/RepoAuditorWeb"
        assert session.is_enterprise is False

    # ----------------------------------------------------------------------
    # Enterprise instances expose the API under a /api/v3 path on the same host.
    def test_EnterpriseUrl(self):
        session = _GetSession("https://github.mycompany.com/gt-csse/RepoAuditorWeb")

        assert session.api_url == "https://github.mycompany.com/api/v3/repos/gt-csse/RepoAuditorWeb"
        assert session.is_enterprise is True

    # ----------------------------------------------------------------------
    def test_EnterpriseUrlPreservesScheme(self):
        session = _GetSession("http://github.mycompany.com/gt-csse/RepoAuditorWeb")

        assert session.api_url == "http://github.mycompany.com/api/v3/repos/gt-csse/RepoAuditorWeb"

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/gt-csse",
            "https://github.com/gt-csse/RepoAuditorWeb/extra",
            "https://github.com",
            # A url without a host has the right number of path parts but no server to query.
            "/gt-csse/RepoAuditorWeb",
        ],
    )
    def test_ErrorInvalidUrl(self, url):
        with pytest.raises(ValueError, match=f"'{url}' is not a valid GitHub repository URL."):
            _GetSession(url)


# ----------------------------------------------------------------------
class TestSessionRequest:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("", "https://api.github.com/repos/gt-csse/RepoAuditorWeb"),
            ("/branches", "https://api.github.com/repos/gt-csse/RepoAuditorWeb/branches"),
            # A relative url without a leading separator is still appended to the api url.
            ("branches", "https://api.github.com/repos/gt-csse/RepoAuditorWeb/branches"),
        ],
    )
    def test_UrlIsRelativeToApiUrl(self, url, expected, monkeypatch):
        requested: list[str] = []

        def Request(self, method, url, *args, **kwargs):  # noqa: ARG001
            requested.append(url)
            return requests.Response()

        monkeypatch.setattr(requests.Session, "request", Request)

        _GetSession().get(url)

        assert requested == [expected]
