import textwrap

from types import SimpleNamespace

import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.contributing import ContributingRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Construct():
    requirement = ContributingRequirement()

    assert requirement.name == "Contributing"
    assert requirement.description == "Validates that CONTRIBUTING exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize("filename", ["CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"])
def test_Found(tmp_path, filename):
    filename = tmp_path / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = ContributingRequirement().Evaluate(
        JOSSModule(), {"repo_dir": SimpleNamespace(name=str(tmp_path))}, {"skip": False, "prohibit": False}
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_NotFound(tmp_path):
    result = ContributingRequirement().Evaluate(
        JOSSModule(), {"repo_dir": SimpleNamespace(name=str(tmp_path))}, {"skip": False, "prohibit": False}
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == "CONTRIBUTING was not found in any of these directories: `.github`, `.`, `docs`."
    assert result.resolution == textwrap.dedent(
        """\
        Add a CONTRIBUTING file to the repository that explains how third parties can contribute
        to the software, report issues or problems with the software, and seek support.
        """,
    )
