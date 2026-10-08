from pathlib import Path
from types import SimpleNamespace

import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.documents import FindPaper
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_references import (
    PaperReferencesRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
@pytest.fixture
def repo_dir(tmp_path):
    # A directory within tmp_path leaves room for files outside of the repository.
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    return repo_dir


# ----------------------------------------------------------------------
def _Evaluate(
    repo_dir: Path,
    paper_text: str,
    bib_text: str | None,
    bibliography: str | None = "paper.bib",
    paper_dir: str = "paper",
):
    (repo_dir / paper_dir).mkdir(exist_ok=True)

    metadata = "" if bibliography is None else f"bibliography: {bibliography}\n"
    (repo_dir / paper_dir / "paper.md").write_text(f"---\n{metadata}---\n{paper_text}", encoding="utf-8")

    if bib_text is not None:
        (repo_dir / paper_dir / "paper.bib").write_text(bib_text, encoding="utf-8")

    # Requirements only read the clone's 'name'.
    return PaperReferencesRequirement().Evaluate(
        JOSSModule(),
        {"repo_dir": SimpleNamespace(name=str(repo_dir)), "paper": FindPaper(repo_dir)},
        {"skip": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PaperReferencesRequirement()

    assert requirement.name == "PaperReferences"
    assert (
        requirement.description
        == "Validates that the paper cites references, and that each citation is defined in its bibliography."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize("bibliography", ["paper.bib", None])
def test_Defined(repo_dir, bibliography):
    result = _Evaluate(
        repo_dir,
        "See [@one; @two:2020, p. 3] and @{three}. Email me@example.com.\n\n```python\n@decorator\n```\n",
        '@article{one,\n}\n@Book{two:2020,\n}\n@misc(three,\n)\n@string{four, = "x"}\n',
        bibliography,
    )

    assert result.result == EvaluateResultValue.Success
    assert (
        result.context
        == "`paper/paper.md` cites 3 reference(s), each of which is defined in `paper/paper.bib`."
    )
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_Undefined(repo_dir):
    # Each non-entry type is shaped like an entry so that only its type excludes its key.
    result = _Evaluate(
        repo_dir,
        "See @one, @two, @three, @four, and @one.\n",
        '@article{one,\n}\n@comment{two,}\n@PREAMBLE{three, "x"}\n@string{four, = "x"}\n',
    )

    assert result.result == EvaluateResultValue.Error
    assert (
        result.context
        == "`paper/paper.md` cites references that are not defined in `paper/paper.bib`: `two`, `three`, `four`."
    )
    assert (
        result.resolution
        == "Add an entry for each undefined reference to `paper/paper.bib`, or correct the citation's identifier in `paper/paper.md`."
    )


# ----------------------------------------------------------------------
def test_NoCitations(repo_dir):
    result = _Evaluate(repo_dir, "No citations.\n", "@article{one,\n}\n")

    assert result.result == EvaluateResultValue.Error
    assert result.context == "`paper/paper.md` does not cite any references."
    assert result.resolution is not None


# ----------------------------------------------------------------------
def test_MissingBibliography(repo_dir):
    result = _Evaluate(repo_dir, "See @one.\n", None, "refs/paper.bib")

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The bibliography `paper/refs/paper.bib` was not found."
    assert result.resolution is not None


# ----------------------------------------------------------------------
def test_BibliographyOutsideRepository(repo_dir):
    (repo_dir.parent / "outside.bib").write_text("@article{one,\n}\n", encoding="utf-8")

    result = _Evaluate(repo_dir, "See @one.\n", "@article{one,\n}\n", "../../outside.bib")

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The bibliography `paper/../../outside.bib` was not found."


# ----------------------------------------------------------------------
# Following symlinks out of the untrusted repository would reveal the contents of files on the host.
def test_SymlinkedBibliographyOutsideRepository(repo_dir):
    (repo_dir.parent / "outside.bib").write_text("@article{one,\n}\n", encoding="utf-8")
    (repo_dir / "paper").mkdir()
    (repo_dir / "paper" / "paper.bib").symlink_to(repo_dir.parent / "outside.bib")

    result = _Evaluate(repo_dir, "See @one.\n", None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The bibliography `paper/paper.bib` was not found."


# ----------------------------------------------------------------------
# The path is validated before the filesystem is accessed, as resolving an untrusted UNC path
# would cause the host to connect to a remote share.
@pytest.mark.parametrize(
    ("paper_dir", "bibliography", "bibliography_path"),
    [
        ("paper", "//attacker.example/share/x.bib", "//attacker.example/share/x.bib"),
        ("paper", "/x.bib", "/x.bib"),
        ("paper", "..\\..\\x.bib", "paper/..\\..\\x.bib"),
        (".", "C:/x.bib", "C:/x.bib"),
    ],
)
def test_UnsafeBibliographyIsNotAccessed(repo_dir, monkeypatch, paper_dir, bibliography, bibliography_path):
    is_file = Path.is_file

    # ----------------------------------------------------------------------
    def IsFile(self) -> bool:
        assert "x.bib" not in str(self)
        return is_file(self)

    # ----------------------------------------------------------------------

    monkeypatch.setattr(Path, "is_file", IsFile)

    result = _Evaluate(repo_dir, "See @one.\n", "@article{one,\n}\n", bibliography, paper_dir)

    assert result.result == EvaluateResultValue.Error
    assert result.context == f"The bibliography `{bibliography_path}` was not found."
