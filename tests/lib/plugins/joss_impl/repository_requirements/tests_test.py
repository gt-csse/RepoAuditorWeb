from types import SimpleNamespace

from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.tests import AutomatedTestsRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Construct():
    requirement = AutomatedTestsRequirement()

    assert requirement.name == "Tests"
    assert (
        requirement.description == "Validates that test or tests or testing or spec exists in the repository."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_Found(tmp_path):
    (tmp_path / "test").mkdir()

    result = AutomatedTestsRequirement().Evaluate(
        JOSSModule(), {"repo_dir": SimpleNamespace(name=str(tmp_path))}, {"skip": False, "prohibit": False}
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_NotFound(tmp_path):
    (tmp_path / "src").mkdir()

    result = AutomatedTestsRequirement().Evaluate(
        JOSSModule(), {"repo_dir": SimpleNamespace(name=str(tmp_path))}, {"skip": False, "prohibit": False}
    )

    assert result.result == EvaluateResultValue.Error
