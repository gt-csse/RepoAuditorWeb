import io
import re

import pytest
import requests

from dbrownell_Common.Streams.DoneManager import DoneManager
from typer.models import OptionInfo

from RepoAuditorWeb.impl.repositories import DisableModulesWithoutUrl, ResolveRepositories
from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module

from conftest import MyModule


# ----------------------------------------------------------------------
def _Resolve(url: str | None, pat: str | None = None, **kwargs) -> tuple[list[str | None], str]:
    output = io.StringIO()

    with DoneManager.Create(output, "Testing...") as dm:
        repositories = ResolveRepositories(dm, url, pat, **kwargs)

    return repositories, output.getvalue()


# ----------------------------------------------------------------------
def _CreateRepository(name: str, *, archived: bool = False, fork: bool = False) -> dict[str, object]:
    return {
        "name": name,
        "html_url": f"https://github.com/my-owner/{name}",
        "archived": archived,
        "fork": fork,
    }


# ----------------------------------------------------------------------
class _FakeGitHub:
    """Returns a canned payload for each requested url and page."""

    # ----------------------------------------------------------------------
    def __init__(self, monkeypatch, responses: dict[tuple[str, int | None], object]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, object]]] = []

        fake = self

        def Request(self, method, url, *args, **kwargs):  # noqa: ARG001
            params = kwargs.get("params") or {}
            fake.requests.append((url, params))

            payload = fake.responses[(url, params.get("page"))]

            response = requests.Response()
            response.status_code = 200
            response.json = lambda: payload  # ty: ignore[invalid-assignment]

            return response

        monkeypatch.setattr(requests.Session, "request", Request)


# ----------------------------------------------------------------------
class TestSingleRepository:
    # ----------------------------------------------------------------------
    # The web form collects the url when it is not provided on the command line.
    def test_NoUrl(self):
        assert _Resolve(None)[0] == [None]

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/gt-csse/RepoAuditorWeb",
            "https://github.mycompany.com/gt-csse/RepoAuditorWeb",
            "file:///repositories/RepoAuditorWeb",
            # Servers other than GitHub may host repositories at the root of the path.
            "https://git.mycompany.com/RepoAuditorWeb",
        ],
    )
    def test_Url(self, url):
        assert _Resolve(url)[0] == [url]

    # ----------------------------------------------------------------------
    # A url that names a GitHub owner most likely omitted the wildcard.
    @pytest.mark.parametrize(
        ("url", "suggestion"),
        [
            ("https://github.com/gt-csse", "https://github.com/gt-csse/*"),
            ("https://github.com/gt-csse/", "https://github.com/gt-csse/*"),
            ("https://www.github.com/gt-csse", "https://www.github.com/gt-csse/*"),
            ("https://GitHub.com/gt-csse", "https://GitHub.com/gt-csse/*"),
            ("https://github.com:443/gt-csse", "https://github.com:443/gt-csse/*"),
            # A query or fragment does not follow the wildcard in the suggestion.
            ("https://github.com/gt-csse/?", "https://github.com/gt-csse/*"),
            ("https://github.com/gt-csse?tab=repositories", "https://github.com/gt-csse/*"),
            ("https://github.com/gt-csse#top", "https://github.com/gt-csse/*"),
        ],
    )
    def test_ErrorOwnerUrl(self, url, suggestion):
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"'{url}' identifies an owner rather than a repository; use '{suggestion}' to audit each of its repositories.",
            ),
        ):
            _Resolve(url)


# ----------------------------------------------------------------------
class TestIncludeOptions:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("option", "kwargs"),
        [
            ("--include-archived", {"include_archived": True}),
            ("--include-forked", {"include_forked": True}),
        ],
    )
    @pytest.mark.parametrize(
        "url",
        [None, "https://github.com/gt-csse/RepoAuditorWeb", "file:///repositories/*"],
    )
    def test_ErrorWithoutGitHubWildcard(self, option, kwargs, url):
        with pytest.raises(
            ValueError,
            match=re.escape(f"'{option}' is only valid with a GitHub url that ends with '/*'."),
        ):
            _Resolve(url, **kwargs)


# ----------------------------------------------------------------------
class TestWildcard:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/gt-csse/Repo*",
            "https://github.com/*/RepoAuditorWeb",
            "https://github.com/gt-*/*",
            "https://*.com/gt-csse/*",
            "https://github.com/gt-csse/*?page=1",
            "https://github.com/gt-csse/*#top",
            "https://github.com/gt-csse/*;type=a",
            "https://github.com/gt-csse/RepoAuditorWeb?filter=*",
        ],
    )
    def test_ErrorPartialWildcard(self, url):
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"'{url}' is not a valid wildcard url; '*' is only supported as the final path segment."
            ),
        ):
            _Resolve(url)

    # ----------------------------------------------------------------------
    def test_ErrorUnsupportedScheme(self):
        with pytest.raises(
            ValueError,
            match=re.escape(
                "'ftp://github.com/gt-csse/*' is not a valid wildcard url; it must begin with 'https://', 'http://', or 'file://'.",
            ),
        ):
            _Resolve("ftp://github.com/gt-csse/*")


# ----------------------------------------------------------------------
class TestGitHubWildcard:
    # ----------------------------------------------------------------------
    def test_Organization(self, monkeypatch):
        fake = _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/my-owner", None): {"type": "Organization"},
                ("https://api.github.com/orgs/my-owner/repos", 1): [
                    _CreateRepository("Second"),
                    _CreateRepository("first"),
                ],
            },
        )

        assert _Resolve("https://github.com/my-owner/*", "my_pat")[0] == [
            "https://github.com/my-owner/first",
            "https://github.com/my-owner/Second",
        ]

        assert fake.requests[-1] == (
            "https://api.github.com/orgs/my-owner/repos",
            {"type": "all", "per_page": 100, "page": 1},
        )

    # ----------------------------------------------------------------------
    def test_User(self, monkeypatch):
        fake = _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/my-owner", None): {"type": "User"},
                ("https://api.github.com/users/my-owner/repos", 1): [_CreateRepository("Repo")],
            },
        )

        repositories, output = _Resolve("https://github.com/my-owner/*")

        assert repositories == ["https://github.com/my-owner/Repo"]
        assert fake.requests[-1] == (
            "https://api.github.com/users/my-owner/repos",
            {"per_page": 100, "page": 1},
        )

        # Unauthenticated requests are heavily rate limited and only list public repositories.
        assert "A PAT was not provided" in output

    # ----------------------------------------------------------------------
    def test_UserWithPatOfAnotherUser(self, monkeypatch):
        fake = _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/my-owner", None): {"type": "User"},
                ("https://api.github.com/user", None): {"login": "someone-else"},
                ("https://api.github.com/users/my-owner/repos", 1): [_CreateRepository("Repo")],
            },
        )

        repositories, output = _Resolve("https://github.com/my-owner/*", "my_pat")

        assert repositories == ["https://github.com/my-owner/Repo"]
        assert fake.requests[-1] == (
            "https://api.github.com/users/my-owner/repos",
            {"per_page": 100, "page": 1},
        )
        assert "A PAT was not provided" not in output

    # ----------------------------------------------------------------------
    # Repositories listed for a user are limited to public ones, so the owner of the PAT lists their
    # own repositories through the authenticated endpoint.
    def test_UserWithOwnPat(self, monkeypatch, tmp_path):
        fake = _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/My-Owner", None): {"type": "User"},
                ("https://api.github.com/user", None): {"login": "my-owner"},
                ("https://api.github.com/user/repos", 1): [_CreateRepository("Private")],
            },
        )

        # The PAT is read from a file when it names one, as it is for the modules.
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text("my_pat\n", encoding="utf-8")

        assert _Resolve("https://github.com/My-Owner/*", str(pat_filename))[0] == [
            "https://github.com/my-owner/Private",
        ]

        assert fake.requests[-1] == (
            "https://api.github.com/user/repos",
            {"affiliation": "owner", "visibility": "all", "per_page": 100, "page": 1},
        )

    # ----------------------------------------------------------------------
    def test_Enterprise(self, monkeypatch):
        _FakeGitHub(
            monkeypatch,
            {
                ("https://github.mycompany.com/api/v3/users/my-owner", None): {"type": "Organization"},
                ("https://github.mycompany.com/api/v3/orgs/my-owner/repos", 1): [_CreateRepository("Repo")],
            },
        )

        assert _Resolve("https://github.mycompany.com/my-owner/*", "my_pat")[0] == [
            "https://github.com/my-owner/Repo",
        ]

    # ----------------------------------------------------------------------
    def test_Pages(self, monkeypatch):
        first_page = [_CreateRepository(f"Repo{index:03}") for index in range(100)]

        _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/my-owner", None): {"type": "Organization"},
                ("https://api.github.com/orgs/my-owner/repos", 1): first_page,
                ("https://api.github.com/orgs/my-owner/repos", 2): [_CreateRepository("Repo100")],
            },
        )

        repositories = _Resolve("https://github.com/my-owner/*", "my_pat")[0]

        assert len(repositories) == 101
        assert repositories[-1] == "https://github.com/my-owner/Repo100"

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({}, ["Repo"]),
            ({"include_archived": True}, ["Archived", "Repo"]),
            ({"include_forked": True}, ["Fork", "Repo"]),
            ({"include_archived": True, "include_forked": True}, ["Archived", "Fork", "Repo"]),
        ],
    )
    def test_ArchivedAndForked(self, monkeypatch, kwargs, expected):
        _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/my-owner", None): {"type": "Organization"},
                ("https://api.github.com/orgs/my-owner/repos", 1): [
                    _CreateRepository("Repo"),
                    _CreateRepository("Archived", archived=True),
                    _CreateRepository("Fork", fork=True),
                ],
            },
        )

        assert _Resolve("https://github.com/my-owner/*", "my_pat", **kwargs)[0] == [
            f"https://github.com/my-owner/{name}" for name in expected
        ]

    # ----------------------------------------------------------------------
    def test_ErrorNoRepositories(self, monkeypatch):
        _FakeGitHub(
            monkeypatch,
            {
                ("https://api.github.com/users/my-owner", None): {"type": "Organization"},
                ("https://api.github.com/orgs/my-owner/repos", 1): [],
            },
        )

        with pytest.raises(
            ValueError, match=re.escape("No repositories were found for 'https://github.com/my-owner/*'.")
        ):
            _Resolve("https://github.com/my-owner/*", "my_pat")

    # ----------------------------------------------------------------------
    # The owner is placed in API paths, where segments such as '..' would change the resource requested.
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/*",
            "https://github.com/../*",
            "https://github.com/a/b/*",
            "https://github.com/%2e%2e/*",
        ],
    )
    def test_ErrorInvalidOwner(self, url):
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"'{url}' is not a valid GitHub wildcard url; it must be in the form '<server>/<owner>/*'.",
            ),
        ):
            _Resolve(url, "my_pat")


# ----------------------------------------------------------------------
class TestLocalWildcard:
    # ----------------------------------------------------------------------
    def test_Repositories(self, tmp_path):
        for name in ["second", "First"]:
            (tmp_path / name / ".git").mkdir(parents=True)

        # A worktree or submodule has a '.git' file rather than a directory.
        (tmp_path / "Worktree").mkdir()
        (tmp_path / "Worktree" / ".git").write_text("gitdir: elsewhere", encoding="utf-8")

        # Directories that are not repositories, hidden directories, and files are not audited.
        (tmp_path / "NotARepository").mkdir()
        (tmp_path / ".hidden" / ".git").mkdir(parents=True)
        (tmp_path / "file.txt").write_text("content", encoding="utf-8")

        assert _Resolve(f"{tmp_path.as_uri()}/*")[0] == [
            (tmp_path / name).resolve().as_uri() for name in ["First", "second", "Worktree"]
        ]

    # ----------------------------------------------------------------------
    # A repository reachable through a symlink is audited once.
    def test_SymlinkIsAuditedOnce(self, tmp_path):
        (tmp_path / "Repo" / ".git").mkdir(parents=True)

        try:
            (tmp_path / "Link").symlink_to(tmp_path / "Repo", target_is_directory=True)
        except OSError:
            pytest.skip("Symlinks are not supported in this environment.")

        assert _Resolve(f"{tmp_path.as_uri()}/*")[0] == [(tmp_path / "Repo").resolve().as_uri()]

    # ----------------------------------------------------------------------
    def test_ErrorNoRepositories(self, tmp_path):
        url = f"{tmp_path.as_uri()}/*"

        with pytest.raises(ValueError, match=re.escape(f"No repositories were found for '{url}'.")):
            _Resolve(url)

    # ----------------------------------------------------------------------
    def test_ErrorNotADirectory(self, tmp_path):
        directory = tmp_path / "missing"

        with pytest.raises(ValueError, match=re.escape(f"'{directory}' is not a directory.")):
            _Resolve(f"{directory.as_uri()}/*")

    # ----------------------------------------------------------------------
    def test_ErrorRemoteHost(self):
        with pytest.raises(
            ValueError,
            match=re.escape(
                "'file://server/share/*' is not a valid wildcard url; a 'file://' url must identify a local directory.",
            ),
        ):
            _Resolve("file://server/share/*")


# ----------------------------------------------------------------------
class TestDisableModulesWithoutUrl:
    # ----------------------------------------------------------------------
    def test_Disabled(self):
        url_parameter = {"url": TyperParameter(str, None, OptionInfo(help="url"))}

        modules: list[Module] = [
            MyModule("WithUrl", "description", [], parameters=url_parameter),
            MyModule("Included", "description", [], requires_explicit_include=True),
            MyModule("Skipped", "description", []),
        ]

        arguments: dict[str, dict[str | None, dict[str, object]]] = {
            "WithUrl": {None: {"skip": False}},
            "Included": {None: {"include": True}, "MyRequirement": {"skip": False}},
            "Skipped": {None: {"skip": False}},
        }

        assert DisableModulesWithoutUrl(modules, arguments) == {
            "WithUrl": {None: {"skip": False}},
            "Included": {None: {"include": False}, "MyRequirement": {"skip": False}},
            "Skipped": {None: {"skip": True}},
        }

        # The arguments are retained for the first repository, so they are not modified.
        assert arguments["Included"][None] == {"include": True}
        assert arguments["Skipped"][None] == {"skip": False}
