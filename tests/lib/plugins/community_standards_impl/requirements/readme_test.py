import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.readme import ReadmeRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a README file to the repository. The README file should provide information about the project, including its purpose, how to install and use it, and any other relevant details. It should be written in a clear and concise manner, and it should be easy to understand for users who are new to the project.
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a README file exists in the repository.

    ## Reasons for this Default

    - GitHub renders the README on the repository's landing page. Without one, visitors see
      only a list of files and must infer the project's purpose from its source.
    - The README is the conventional place to document how to install, use, and contribute
      to the project, which reduces the number of questions maintainers must answer
      individually.
    - Package registries, such as PyPI and npm, commonly publish the README as the project's
      long description, so its absence carries over to those listings.
    - GitHub's community profile checklist includes a README, and its absence is visible to
      anyone evaluating the project's health.

    ## Reasons to Override this Default

    - The repository is not intended to be read by others, such as a mirror, an archive of
      generated artifacts, or a scratch repository, so there is no audience for the file.
    - The repository's purpose is fully described elsewhere, such as in the documentation of
      a parent project that links to it, and a README would duplicate that content.

    Note that when more than one README exists, GitHub displays the one in the `.github`
    directory first, then the repository root, and finally the `docs` directory.
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
    requirement = ReadmeRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = ReadmeRequirement()

    assert requirement.name == "Readme"
    assert requirement.description == "Validates that README exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        "README.md",
        "README.rst",
        "README.txt",
        "README",
        "readme.md",
        "Readme.adoc",
        ".github/README.md",
        "docs/README.markdown",
    ],
)
def test_Found(repo, filename):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Success
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_NotFound(repo):
    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "README was not found in any of these directories: `.`, `docs`, `.github`."
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
