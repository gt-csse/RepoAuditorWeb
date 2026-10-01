import re

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.repository_arguments import (
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
