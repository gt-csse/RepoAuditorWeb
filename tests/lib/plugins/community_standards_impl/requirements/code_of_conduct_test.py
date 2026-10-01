import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.code_of_conduct import (
    CodeOfConductRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a CODE_OF_CONDUCT file to the repository. The file should define the standards of behavior expected from contributors, describe unacceptable behavior, and explain how to report violations and how they will be enforced. Adopting an established code of conduct, such as the Contributor Covenant, is a common approach.
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    A CODE_OF_CONDUCT file establishes expectations for how participants in the project interact with one another. It signals that the project is a welcoming and inclusive environment, and it provides a documented process for addressing abusive or unwelcome behavior.
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
    requirement = CodeOfConductRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = CodeOfConductRequirement()

    assert requirement.name == "CodeOfConduct"
    assert requirement.description == "Validates that CODE_OF_CONDUCT exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        "CODE_OF_CONDUCT.md",
        "CODE_OF_CONDUCT.txt",
        "CODE_OF_CONDUCT",
        "code_of_conduct.md",
        "Code_Of_Conduct.rst",
        ".github/CODE_OF_CONDUCT.md",
        "docs/CODE_OF_CONDUCT.md",
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
    assert (
        result.context == "CODE_OF_CONDUCT was not found in any of these directories: `.`, `docs`, `.github`."
    )
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
