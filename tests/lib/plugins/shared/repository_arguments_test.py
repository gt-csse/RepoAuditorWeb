import re

import pytest

from RepoAuditorWeb.lib.plugins.shared.repository_arguments import (
    GetRepositoryParameters,
    RepositoryArguments,
    ResolvePat,
    ResolveRepositoryArguments,
)


# ----------------------------------------------------------------------
def test_GetRepositoryParameters():
    parameters = GetRepositoryParameters()

    assert list(parameters.keys()) == ["url", "pat", "branch"]
    assert parameters["url"].type is str
    assert parameters["url"].default is None
    assert parameters["pat"].type == (str | None)
    assert parameters["pat"].default is None
    # The environment variable is bound once, by the common `--pat` option.
    assert parameters["pat"].info.envvar is None  # ty: ignore[unresolved-attribute]
    assert parameters["branch"].type == (str | None)
    assert parameters["branch"].default is None


# ----------------------------------------------------------------------
class TestResolveRepositoryArguments:
    # ----------------------------------------------------------------------
    def test_Values(self, pat_filename):
        assert ResolveRepositoryArguments(
            {
                "url": "https://github.com/gt-csse/RepoAuditorWeb",
                "pat": pat_filename,
                "branch": "my_branch",
            },
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", "my_pat", "my_branch")

    # ----------------------------------------------------------------------
    def test_OptionalArgumentsAreAbsent(self):
        assert ResolveRepositoryArguments(
            {"url": "https://github.com/gt-csse/RepoAuditorWeb"},
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", None, None)

    # ----------------------------------------------------------------------
    # The url is passed to git, which would otherwise accept bare paths and other transports.
    @pytest.mark.parametrize(
        "url",
        [
            "/local/path",
            "C:/local/path",
            "ssh://git@github.com/a/b",
            "git@github.com:a/b",
            "https://",
            "file://",
        ],
    )
    def test_ErrorInvalidUrl(self, url):
        with pytest.raises(ValueError) as exc_info:
            ResolveRepositoryArguments({"url": url})

        assert str(exc_info.value) == (
            f"'{url}' is not a valid repository URL; it must begin with 'https://', 'http://', or 'file://'."
        )

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("url", ["http://github.example.com/a/b", "file:///local/repository"])
    def test_OtherSchemes(self, url):
        assert ResolveRepositoryArguments({"url": url}) == RepositoryArguments(url, None, None)

    # ----------------------------------------------------------------------
    # Wildcards are only expanded on the command line, so one entered elsewhere (such as the web form)
    # is reported rather than passed to git or the GitHub API.
    @pytest.mark.parametrize("url", ["https://github.com/gt-csse/*", "file:///repositories/*"])
    def test_ErrorWildcard(self, url):
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"'{url}' contains a wildcard; wildcard urls are only supported on the command line."
            ),
        ):
            ResolveRepositoryArguments({"url": url})

    # ----------------------------------------------------------------------
    # The contents are sent as a credential, so a file holding anything other than a single token is
    # rejected without its contents appearing in the error.
    @pytest.mark.parametrize("content", ["first_secret\nsecond_secret\n", "", " \t\n "])
    def test_ErrorPatFileContent(self, tmp_path, content):
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text(content, encoding="utf-8")

        with pytest.raises(ValueError) as exc_info:
            ResolveRepositoryArguments(
                {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": str(pat_filename)},
            )

        assert str(exc_info.value) == f"'{pat_filename}' does not contain a Personal Access Token."

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("branch", ["main", "feature/my-branch", "release-1.0", "my#branch"])
    def test_Branch(self, branch):
        assert ResolveRepositoryArguments(
            {"url": "https://github.com/gt-csse/RepoAuditorWeb", "branch": branch},
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", None, branch)

    # ----------------------------------------------------------------------
    # The branch is placed in API paths, where these names would change the resource requested.
    @pytest.mark.parametrize(
        "branch",
        [
            "",
            "..",
            "../../collaborators",
            "a/../b",
            ".hidden",
            "a/.b",
            "/a",
            "a/",
            "a//b",
            "a b",
            "a?b",
            "a.lock",
            "a@{0}",
            "a\\b",
        ],
    )
    def test_ErrorInvalidBranch(self, branch):
        with pytest.raises(ValueError) as exc_info:
            ResolveRepositoryArguments({"url": "https://github.com/gt-csse/RepoAuditorWeb", "branch": branch})

        assert str(exc_info.value) == f"'{branch}' is not a valid branch name."

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("values", [{}, {"url": None}])
    def test_ErrorMissingUrl(self, values):
        with pytest.raises(ValueError, match=re.escape("'url' is a required argument for this module.")):
            ResolveRepositoryArguments(values)

    # ----------------------------------------------------------------------
    # The value is not echoed in the error, as it may be a token entered directly.
    @pytest.mark.parametrize(
        "pat", ["my_pat", "", " ", "does_not_exist.txt", ".", "~no_such_user_for_test/pat.txt"]
    )
    def test_ErrorPatNotFile(self, pat):
        with pytest.raises(ValueError) as exc_info:
            ResolveRepositoryArguments({"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": pat})

        assert str(exc_info.value) == "'pat' must be the path to a file containing a Personal Access Token."


# ----------------------------------------------------------------------
class TestResolvePat:
    # ----------------------------------------------------------------------
    def test_None(self):
        assert ResolvePat(None) is None

    # ----------------------------------------------------------------------
    def test_File(self, pat_filename):
        assert ResolvePat(pat_filename) == "my_pat"

    # ----------------------------------------------------------------------
    def test_FileInHomeDirectory(self, tmp_path, monkeypatch):
        # Windows resolves '~' with USERPROFILE and ignores HOME.
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        (tmp_path / "pat.txt").write_text("my_file_pat", encoding="utf-8")

        assert ResolvePat("~/pat.txt") == "my_file_pat"
