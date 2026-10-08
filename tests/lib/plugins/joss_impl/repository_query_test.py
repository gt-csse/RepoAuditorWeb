from pathlib import Path

import git
import pytest

from RepoAuditorWeb.lib.plugins.joss_impl import repository_query
from RepoAuditorWeb.lib.plugins.joss_impl.documents import Document
from RepoAuditorWeb.lib.plugins.joss_impl.repository_query import RepositoryQuery


# ----------------------------------------------------------------------
def test_Construct():
    query = RepositoryQuery()

    assert query.name == "Repository"
    assert [requirement.name for requirement in query.requirements] == [
        "StatementOfNeed",
        "Installation",
        "ExampleUsage",
        "Documentation",
        "Tests",
        "Contributing",
        "Paper",
        "PaperMetadata",
        "PaperSections",
        "PaperLength",
        "PaperReferences",
    ]


# ----------------------------------------------------------------------
def test_GetQueryData(monkeypatch):
    # ----------------------------------------------------------------------
    def CloneFrom(url: str, to_path: str, **kwargs) -> None:  # noqa: ARG001
        (Path(to_path) / "README.md").write_text("# Title\n", encoding="utf-8")
        (Path(to_path) / "paper").mkdir()
        (Path(to_path) / "paper" / "paper.md").write_text(
            "---\ntitle: Title\n---\n# Summary\n", encoding="utf-8"
        )

    # ----------------------------------------------------------------------

    monkeypatch.setattr(git.Repo, "clone_from", CloneFrom)

    query = RepositoryQuery()
    query_data = query.GetQueryData({"url": "https://github.com/owner/repo", "pat": None, "branch": None})

    try:
        assert query_data is not None
        assert query_data["readme"] == Document("README.md", "# Title\n")

        paper = query_data["paper"]
        assert paper is not None
        assert paper.path == "paper/paper.md"  # ty: ignore[unresolved-attribute]
        assert paper.metadata == {"title": "Title"}  # ty: ignore[unresolved-attribute]
    finally:
        assert query_data is not None
        query.CleanupQueryData(query_data)


# ----------------------------------------------------------------------
# CleanupQueryData is not invoked when GetQueryData raises, so the query removes the clone itself.
def test_GetQueryDataErrorRemovesClone(monkeypatch):
    repo_dirs: list[Path] = []

    # ----------------------------------------------------------------------
    def CloneFrom(url: str, to_path: str, **kwargs) -> None:  # noqa: ARG001
        repo_dirs.append(Path(to_path))

    # ----------------------------------------------------------------------
    def FindPaper(repo_dir: Path) -> None:  # noqa: ARG001
        raise OSError("My error.")

    # ----------------------------------------------------------------------

    monkeypatch.setattr(git.Repo, "clone_from", CloneFrom)
    monkeypatch.setattr(repository_query, "FindPaper", FindPaper)

    # The bound exception's traceback keeps the TemporaryDirectory alive, so its finalizer cannot remove the clone.
    with pytest.raises(OSError, match="My error.") as ex_info:
        RepositoryQuery().GetQueryData({"url": "https://github.com/owner/repo", "pat": None, "branch": None})

    assert len(repo_dirs) == 1
    assert not repo_dirs[0].exists()
