import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.issue_template import (
    IssueTemplateRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add one or more issue templates to the `.github/ISSUE_TEMPLATE` directory. Each template should prompt the reporter for the information maintainers need to act on the issue, such as steps to reproduce, expected and actual behavior, and environment details for bug reports, or the motivation and proposed solution for feature requests. GitHub only shows a template in the community profile when it defines `name` and `about` in its YAML front matter (Markdown templates) or `name` and `description` (issue forms).

    GitHub supports two kinds of issue templates:

    - [Issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository#creating-issue-templates), written in Markdown with YAML front matter.
    - [Issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms), written in YAML and rendered as web forms with required fields and validation.
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that an ISSUE_TEMPLATE directory exists in the `.github` directory.

    ## Reasons for this Default

    - GitHub presents issue templates when a user opens a new issue, so reporters are prompted
      for the details maintainers need before the issue is submitted.
    - Structured reports reduce the back-and-forth required to reproduce bugs or understand
      feature requests, shortening the time to triage.
    - Separate templates for bugs, feature requests, and questions make it easier to label
      and route issues consistently.
    - GitHub's community profile checklist includes issue templates, and their absence is
      visible to anyone evaluating the project's health.

    ## Reasons to Override this Default

    - The organization provides default issue templates in its `.github` repository.
      GitHub displays those templates for repositories that do not define their own, but this
      requirement only inspects the repository itself and will not detect them.
    - Issues are disabled for the repository, or issues are tracked in an external system,
      so templates would never be shown.
    - The repository receives few issues, such as a personal or archived repository, and the
      overhead of maintaining templates outweighs their benefit.

    Note that this requirement only checks that the `.github/ISSUE_TEMPLATE` directory exists.
    It does not validate the templates within it, so a directory containing only a `config.yml`
    file, or templates without the front matter GitHub requires, will still be detected.
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
    requirement = IssueTemplateRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = IssueTemplateRequirement()

    assert requirement.name == "IssueTemplate"
    assert requirement.description == "Validates that ISSUE_TEMPLATE exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("filename", "location"),
    [
        (".github/ISSUE_TEMPLATE/bug_report.md", ".github/ISSUE_TEMPLATE"),
        (".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE"),
        (".github/issue_template/bug_report.md", ".github/issue_template"),
    ],
)
def test_Found(repo, filename, location):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Success
    assert result.context == f"ISSUE_TEMPLATE was found at `{location}`."
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# Legacy locations that GitHub no longer recognizes.
@pytest.mark.parametrize(
    "filename",
    [
        "ISSUE_TEMPLATE/bug_report.md",
        "docs/ISSUE_TEMPLATE/bug_report.md",
        "ISSUE_TEMPLATE.md",
        "docs/ISSUE_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE.md",
    ],
)
def test_NotFound(repo, filename):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "ISSUE_TEMPLATE was not found in the `.github` directory."
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
