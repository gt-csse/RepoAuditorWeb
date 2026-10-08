from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper import PaperRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PaperRequirement()

    assert requirement.name == "Paper"
    assert requirement.description == "Validates that a JOSS paper (`paper.md`) exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_Found():
    result = PaperRequirement().Evaluate(
        JOSSModule(), {"paper": Paper("paper/paper.md", "", {}, None)}, {"skip": False}
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context == "The paper was found at `paper/paper.md`."
    assert result.resolution is None
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_NotFound():
    result = PaperRequirement().Evaluate(JOSSModule(), {"paper": None}, {"skip": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == "`paper.md` was not found in the repository."
    assert result.resolution is not None
