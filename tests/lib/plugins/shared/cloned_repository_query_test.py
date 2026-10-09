import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import git
import pytest

from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import (
    ClonedRepositoryQuery,
    GetRepositoryDirectory,
    IsWithinRepository,
)


# ----------------------------------------------------------------------
class _CloneRecorder:
    """Stands in for git.Repo.clone_from so that no network calls are made."""

    # ----------------------------------------------------------------------
    def __init__(self, exception: Exception | None = None) -> None:
        self.exception = exception
        self.calls: list[tuple[str, str, dict[str, object]]] = []

    # ----------------------------------------------------------------------
    def __call__(self, url: str, to_path: str, **kwargs) -> None:
        self.calls.append((url, to_path, kwargs))

        if self.exception is not None:
            raise self.exception


# ----------------------------------------------------------------------
@pytest.fixture
def clone_recorder(monkeypatch):
    recorder = _CloneRecorder()
    monkeypatch.setattr(git.Repo, "clone_from", recorder)

    return recorder


# ----------------------------------------------------------------------
def _CreateQuery() -> ClonedRepositoryQuery:
    return ClonedRepositoryQuery("MyQuery", [])


# ----------------------------------------------------------------------
def _CreateModuleData(pat: str | None = None, branch: str | None = None) -> dict[str, object]:
    return {"url": "https://github.com/gt-csse/RepoAuditorWeb", "pat": pat, "branch": branch}


# ----------------------------------------------------------------------
class TestGetQueryData:
    # ----------------------------------------------------------------------
    def test_ClonesIntoRepoDir(self, clone_recorder):
        query = _CreateQuery()
        query_data = query.GetQueryData(_CreateModuleData())

        assert query_data is not None

        repo_dir = query_data["repo_dir"]
        assert isinstance(repo_dir, TemporaryDirectory)
        assert Path(repo_dir.name).is_dir()  # ty: ignore[invalid-argument-type]

        query.CleanupQueryData(query_data)

        assert clone_recorder.calls == [
            (
                "https://github.com/gt-csse/RepoAuditorWeb",
                repo_dir.name,
                {"branch": None, "depth": 1},
            ),
        ]

    # ----------------------------------------------------------------------
    def test_Branch(self, clone_recorder):
        query = _CreateQuery()
        query_data = query.GetQueryData(_CreateModuleData(branch="my_branch"))

        assert query_data is not None
        query.CleanupQueryData(query_data)

        assert clone_recorder.calls[0][2] == {"branch": "my_branch", "depth": 1}

    # ----------------------------------------------------------------------
    # The PAT is embedded in the url so that private repositories can be cloned without prompting.
    def test_Pat(self, clone_recorder):
        query = _CreateQuery()
        query_data = query.GetQueryData(_CreateModuleData(pat="my_pat"))

        assert query_data is not None
        query.CleanupQueryData(query_data)

        assert clone_recorder.calls[0][0] == "https://my_pat@github.com/gt-csse/RepoAuditorWeb"

    # ----------------------------------------------------------------------
    # A 'file://' url has no host, so embedding the PAT would produce an invalid url.
    def test_PatWithFileUrl(self, clone_recorder):
        module_data = _CreateModuleData(pat="my_pat")
        module_data["url"] = "file:///repos/my_repo"

        query = _CreateQuery()
        query_data = query.GetQueryData(module_data)

        assert query_data is not None
        query.CleanupQueryData(query_data)

        assert clone_recorder.calls[0][0] == "file:///repos/my_repo"

    # ----------------------------------------------------------------------
    # The PAT is never sent over an unencrypted connection.
    def test_PatWithHttpUrl(self, clone_recorder):
        module_data = _CreateModuleData(pat="my_pat")
        module_data["url"] = "http://github.com/gt-csse/RepoAuditorWeb"

        query = _CreateQuery()
        query_data = query.GetQueryData(module_data)

        assert query_data is not None
        query.CleanupQueryData(query_data)

        assert clone_recorder.calls[0][0] == "https://my_pat@github.com/gt-csse/RepoAuditorWeb"

    # ----------------------------------------------------------------------
    def test_ErrorCloneRemovesRepoDir(self, clone_recorder):
        clone_recorder.exception = ValueError("My clone error.")

        with pytest.raises(RuntimeError):
            _CreateQuery().GetQueryData(_CreateModuleData())

        assert not Path(clone_recorder.calls[0][1]).exists()

    # ----------------------------------------------------------------------
    # A PAT containing URL delimiters must not change the host that is contacted.
    def test_PatIsEncoded(self, clone_recorder):
        query = _CreateQuery()
        query_data = query.GetQueryData(_CreateModuleData(pat="my@attacker.example/x:y"))

        assert query_data is not None
        query.CleanupQueryData(query_data)

        assert clone_recorder.calls[0][0] == (
            "https://my%40attacker.example%2Fx%3Ay@github.com/gt-csse/RepoAuditorWeb"
        )

    # ----------------------------------------------------------------------
    # The url git reports holds the encoded PAT, which must be redacted as well.
    def test_ErrorCloneWithEncodedPat(self, clone_recorder):
        clone_recorder.exception = ValueError("git clone https://my%40pat@github.com/gt-csse/RepoAuditorWeb")

        with pytest.raises(RuntimeError) as exc_info:
            _CreateQuery().GetQueryData(_CreateModuleData(pat="my@pat"))

        assert "Error: git clone https://***@github.com/gt-csse/RepoAuditorWeb\n" in str(exc_info.value)

    # ----------------------------------------------------------------------
    # The module data is augmented in place rather than replaced, so existing values are preserved.
    def test_PreservesModuleData(self, clone_recorder):  # noqa: ARG002
        module_data = _CreateModuleData(pat="my_pat", branch="my_branch")

        query = _CreateQuery()
        query_data = query.GetQueryData(module_data)

        assert query_data is not None
        query.CleanupQueryData(query_data)

        assert query_data is module_data
        assert query_data["url"] == "https://github.com/gt-csse/RepoAuditorWeb"
        assert query_data["pat"] == "my_pat"
        assert query_data["branch"] == "my_branch"

    # ----------------------------------------------------------------------
    def test_ErrorCloneWithoutPat(self, clone_recorder):
        clone_recorder.exception = ValueError("My clone error.")

        with pytest.raises(RuntimeError) as exc_info:
            _CreateQuery().GetQueryData(_CreateModuleData())

        assert str(exc_info.value) == textwrap.dedent(
            """\
            An error occurred while attempting to clone the target repository.

            If you are auditing a private repository, please provide a PAT with access to the repository. A fine-grained PAT must grant the `Contents: Read` repository permission; a classic PAT must have the `repo` scope.

            Error: My clone error.
            """,
        )
        assert exc_info.value.__cause__ is clone_recorder.exception

    # ----------------------------------------------------------------------
    # git includes the clone url in its output, so the PAT embedded in that url must not reach the user.
    def test_ErrorCloneWithPat(self, clone_recorder):
        clone_recorder.exception = ValueError(
            "Cmd('git') failed: git clone https://my_pat@github.com/gt-csse/RepoAuditorWeb (my_pat)",
        )

        with pytest.raises(RuntimeError) as exc_info:
            _CreateQuery().GetQueryData(_CreateModuleData(pat="my_pat"))

        assert str(exc_info.value) == textwrap.dedent(
            """\
            An error occurred while attempting to clone the target repository.

            If you are auditing a private repository, please ensure your PAT has access to the repository. A fine-grained PAT must grant the `Contents: Read` repository permission; a classic PAT must have the `repo` scope.

            Error: Cmd('git') failed: git clone https://***@github.com/gt-csse/RepoAuditorWeb (***)
            """,
        )
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__ is True


# ----------------------------------------------------------------------
def test_CleanupQueryDataRemovesRepoDir(clone_recorder):  # noqa: ARG001
    query = _CreateQuery()
    query_data = query.GetQueryData(_CreateModuleData())

    assert query_data is not None
    repo_dir = Path(query_data["repo_dir"].name)  # ty: ignore[unresolved-attribute]
    (repo_dir / "README.md").write_text("content", encoding="utf-8")

    query.CleanupQueryData(query_data)

    assert not repo_dir.exists()


# ----------------------------------------------------------------------
def test_GetRepositoryDirectory():
    repo_dir = TemporaryDirectory()

    try:
        assert GetRepositoryDirectory({"repo_dir": repo_dir}) == Path(repo_dir.name).resolve()
    finally:
        repo_dir.cleanup()


# ----------------------------------------------------------------------
def test_IsWithinRepository(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    (tmp_path / "outside.md").write_text("content", encoding="utf-8")
    (repo_dir / "link.md").symlink_to(tmp_path / "outside.md")

    assert IsWithinRepository(repo_dir, repo_dir / "file") is True
    assert IsWithinRepository(repo_dir, repo_dir / ".." / "file") is False
    assert IsWithinRepository(repo_dir, tmp_path / "other") is False
    assert IsWithinRepository(repo_dir, repo_dir / "link.md") is False
