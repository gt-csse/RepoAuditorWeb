import re

import pytest

from RepoAuditorWeb.lib.plugins.shared.repository_arguments import (
    GetRepositoryParameters,
    RepositoryArguments,
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
    def test_Values(self):
        assert ResolveRepositoryArguments(
            {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": "my_pat", "branch": "my_branch"},
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", "my_pat", "my_branch")

    # ----------------------------------------------------------------------
    def test_OptionalArgumentsAreAbsent(self):
        assert ResolveRepositoryArguments(
            {"url": "https://github.com/gt-csse/RepoAuditorWeb"},
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", None, None)

    # ----------------------------------------------------------------------
    def test_PatIsStripped(self):
        assert ResolveRepositoryArguments(
            {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": "  my_pat\n"},
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", "my_pat", None)

    # ----------------------------------------------------------------------
    def test_PatFromFile(self, tmp_path):
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text("  my_file_pat\n", encoding="utf-8")

        assert ResolveRepositoryArguments(
            {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": str(pat_filename)},
        ) == RepositoryArguments("https://github.com/gt-csse/RepoAuditorWeb", "my_file_pat", None)

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
    # The contents are sent as a credential, so a file holding anything other than a single token is
    # rejected without its contents appearing in the error.
    def test_ErrorPatFileWithMultipleValues(self, tmp_path):
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text("first_secret\nsecond_secret\n", encoding="utf-8")

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
    @pytest.mark.parametrize("pat", ["", " ", " \t\n "])
    def test_ErrorWhitespacePat(self, pat):
        with pytest.raises(
            ValueError, match=re.escape("'pat' must not be empty or contain only whitespace.")
        ):
            ResolveRepositoryArguments({"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": pat})

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("content", ["", " \t\n "])
    def test_ErrorWhitespacePatFromFile(self, tmp_path, content):
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text(content, encoding="utf-8")

        with pytest.raises(
            ValueError, match=re.escape("'pat' must not be empty or contain only whitespace.")
        ):
            ResolveRepositoryArguments(
                {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": str(pat_filename)},
            )
