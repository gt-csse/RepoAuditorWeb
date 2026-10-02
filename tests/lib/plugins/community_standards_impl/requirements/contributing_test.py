import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.contributing import (
    ContributingRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a CONTRIBUTING file to the repository. The file should explain how to report issues, propose changes, set up a development environment, run tests, and submit pull requests, along with any coding conventions or review expectations the project enforces.

    GitHub references these CONTRIBUTING files as examples:

    - [GitHub Docs](https://github.com/github/docs/blob/main/CONTRIBUTING.md)
    - [Ruby on Rails](https://github.com/rails/rails/blob/main/CONTRIBUTING.md)
    - [Open Government](https://github.com/opengovernment/opengovernment/blob/master/CONTRIBUTING.md)
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a CONTRIBUTING file exists in the repository.

    ## Reasons for this Default

    - GitHub links to the CONTRIBUTING file when contributors open an issue or pull request,
      so guidelines are presented at the moment they are most relevant.
    - Documenting the contribution process up front reduces the number of submissions that
      must be returned for missing tests, incorrect formatting, or an unexpected workflow.
    - The file lowers the barrier for first-time contributors, who otherwise must infer the
      project's expectations from its history or ask a maintainer directly.
    - GitHub's community profile checklist includes a CONTRIBUTING file, and its absence is
      visible to anyone evaluating the project's health.

    ## Reasons to Override this Default

    - The organization provides a default CONTRIBUTING file in its `.github` repository.
      GitHub displays that file for repositories that do not define their own, but this
      requirement only inspects the repository itself and will not detect it.
    - The repository does not accept outside contributions, such as a personal, mirrored, or
      archived repository, so there is no process to document.
    - Contribution guidelines are maintained elsewhere, such as in a parent project's
      documentation, and a CONTRIBUTING file would duplicate that content.

    Note that a CONTRIBUTING file should be kept in sync with the project's tooling; outdated
    setup or testing instructions can be more confusing to contributors than none at all.
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
    requirement = ContributingRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = ContributingRequirement()

    assert requirement.name == "Contributing"
    assert requirement.description == "Validates that CONTRIBUTING exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        "CONTRIBUTING.md",
        "CONTRIBUTING.txt",
        "CONTRIBUTING",
        "contributing.md",
        "Contributing.rst",
        ".github/CONTRIBUTING.md",
        "docs/CONTRIBUTING.md",
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
    assert result.context == "CONTRIBUTING was not found in any of these directories: `.github`, `.`, `docs`."
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
