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
    A README file is a text file that contains information about the project, such as its purpose, how to install and use it, and any other relevant details. It is typically the first file that users see when they visit a project's repository, and it serves as a guide for understanding the project and getting started with it.
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

    assert requirement.name == "README"
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
