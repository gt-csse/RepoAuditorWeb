import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.scientific_software_impl.requirements.citation import CitationRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a `CITATION.cff` file to the root of the repository. The file should describe how to cite the software, including its title, authors, version, release date, and any DOI or associated publication.

    See [About CITATION files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) for more information.
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a CITATION or CITATIONS file exists in the repository.

    ## Reasons for this Default

    - Researchers who use the software need to know how to cite it; without explicit
      instructions, citations are often omitted or inconsistent.
    - Consistent citations allow the authors to receive credit for their work and allow
      funders to measure the software's impact.
    - GitHub displays a "Cite this repository" link for `CITATION.cff` files in the
      repository root, and services such as Zenodo use the file to populate archive metadata.

    ## Reasons to Override this Default

    - The software is not intended to be used or cited in research, such as a personal,
      mirrored, or archived repository.
    - Citation information is provided elsewhere, such as in the documentation of a parent
      project that links to this repository.
    """,
)


# ----------------------------------------------------------------------
@pytest.fixture
def repo():
    repo_dir = TemporaryDirectory()

    yield repo_dir

    repo_dir.cleanup()


# ----------------------------------------------------------------------
def _Evaluate(repo: TemporaryDirectory) -> EvaluateResult:
    requirement = CitationRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = CitationRequirement()

    assert requirement.name == "Citation"
    assert requirement.description == "Validates that CITATION or CITATIONS exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        "CITATION.cff",
        "CITATION",
        "citation.cff",
        "CITATIONS",
        "CITATIONS.md",
        "inst/CITATION",
        "inst/CITATIONS",
    ],
)
def test_Found(repo, filename):
    location = filename
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Success
    assert result.context == f"CITATION or CITATIONS was found at `{location}`."
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        "docs/CITATION.cff",
        ".github/CITATION.cff",
        "CITATION_INFO.md",
    ],
)
def test_NotFound(repo, filename):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "CITATION or CITATIONS was not found in any of these directories: `.`, `inst`."
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
