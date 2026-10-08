from types import SimpleNamespace

import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.documentation import (
    DocumentationRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Construct():
    requirement = DocumentationRequirement()

    assert requirement.name == "Documentation"
    assert (
        requirement.description
        == "Validates that docs or doc or documentation or vignettes exists in the repository."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize("directory", ["docs", "vignettes"])
def test_Found(tmp_path, directory):
    (tmp_path / directory).mkdir()

    result = DocumentationRequirement().Evaluate(
        JOSSModule(), {"repo_dir": SimpleNamespace(name=str(tmp_path))}, {"skip": False, "prohibit": False}
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_NotFound(tmp_path):
    (tmp_path / "documents").mkdir()

    result = DocumentationRequirement().Evaluate(
        JOSSModule(), {"repo_dir": SimpleNamespace(name=str(tmp_path))}, {"skip": False, "prohibit": False}
    )

    assert result.result == EvaluateResultValue.Error
