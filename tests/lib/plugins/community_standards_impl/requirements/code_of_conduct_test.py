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

    GitHub provides these templates when adding a CODE_OF_CONDUCT file through its web interface:

    - [Contributor Covenant](https://www.contributor-covenant.org/)
    - [Citizen Code of Conduct](https://github.com/stumpsyn/policies/blob/master/citizen_code_of_conduct.md)
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a CODE_OF_CONDUCT file exists in the repository.

    ## Reasons for this Default

    - A code of conduct establishes expectations for how participants interact before a
      conflict occurs. Enforcement decisions that cite a published standard are easier to
      justify and less likely to appear arbitrary than decisions made case by case.
    - The file documents how to report abusive or unwelcome behavior, giving participants a
      known channel rather than requiring them to find a maintainer to contact.
    - Its presence signals that the project is a welcoming environment, which some
      contributors and organizations consider before participating.
    - Established templates, such as the Contributor Covenant, make adoption inexpensive.

    ## Reasons to Override this Default

    - The organization provides a default CODE_OF_CONDUCT file in its `.github` repository.
      GitHub displays that file for repositories that do not define their own, but this
      requirement only inspects the repository itself and will not detect it.
    - The repository does not accept outside participation, such as a personal or internal
      repository, so there is no community for the file to govern.
    - Participant conduct is already governed by a policy outside the repository, such as an
      employer's code of conduct for an internal project.

    Note that a code of conduct is only as effective as its enforcement; the reporting
    contact listed in the file should be monitored by someone with the authority to act.
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
        result.context == "CODE_OF_CONDUCT was not found in any of these directories: `.github`, `.`, `docs`."
    )
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
