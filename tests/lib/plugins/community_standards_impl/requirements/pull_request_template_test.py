import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.pull_request_template import (
    PullRequestTemplateRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a `pull_request_template.md` file to the `.github` directory, the root of the repository, or the `docs` directory. GitHub automatically populates the body of every new pull request with the template's contents, so it should prompt the author for the information reviewers need, such as a summary of the change, related issues, testing performed, and a checklist of project conventions.

    See [Creating a pull request template for your repository](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository) for more information.
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a PULL_REQUEST_TEMPLATE file exists in the repository.

    ## Reasons for this Default

    - GitHub populates new pull requests with the template, so authors are prompted for the
      details reviewers need before the pull request is submitted.
    - Consistent pull request descriptions make changes easier to review, and make the
      project's history easier to understand after the pull request is merged.
    - A checklist within the template reminds authors of project conventions, such as adding
      tests or updating documentation, reducing the number of review iterations.
    - GitHub's community profile checklist includes a pull request template, and its absence
      is visible to anyone evaluating the project's health.

    ## Reasons to Override this Default

    - The organization provides a default pull request template in its `.github` repository.
      GitHub uses that template for repositories that do not define their own, but this
      requirement only inspects the repository itself and will not detect it.
    - The repository does not accept pull requests, such as a personal, mirrored, or archived
      repository, so the template would never be shown.
    - Pull request templates are stored in a `PULL_REQUEST_TEMPLATE` directory. GitHub only
      applies those templates when they are selected via a query parameter, and this
      requirement will not detect them.
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
    requirement = PullRequestTemplateRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PullRequestTemplateRequirement()

    assert requirement.name == "PullRequestTemplate"
    assert requirement.description == "Validates that PULL_REQUEST_TEMPLATE exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        ".github/pull_request_template.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "pull_request_template.md",
        "PULL_REQUEST_TEMPLATE",
        "docs/pull_request_template.md",
    ],
)
def test_Found(repo, filename):
    location = filename
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Success
    assert result.context == f"PULL_REQUEST_TEMPLATE was found at `{location}`."
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        # Templates within a directory are only applied when selected via a query parameter.
        ".github/PULL_REQUEST_TEMPLATE/feature.md",
        # Locations that GitHub does not search.
        "src/pull_request_template.md",
    ],
)
def test_NotFound(repo, filename):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Error
    assert (
        result.context
        == "PULL_REQUEST_TEMPLATE was not found in any of these directories: `.github`, `.`, `docs`."
    )
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
