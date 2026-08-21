import pytest

from RepoAuditorWeb.lib.plugins.github_impl.template_requirement import TemplateRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue


# ----------------------------------------------------------------------
def _Evaluate(response: dict, *, require: bool = False) -> EvaluateResult:
    return TemplateRequirement().Evaluate({"response": response}, {"skip": False, "require": require})


# ----------------------------------------------------------------------
def test_Construct():
    requirement = TemplateRequirement()

    assert requirement.name == "Template"
    assert requirement.description == "Requirement to validate a repository's template status."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = TemplateRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("is_template", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(is_template, require):
    result = _Evaluate({"is_template": is_template}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_TemplateWhenNotRequired():
    result = _Evaluate({"is_template": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's template status is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NotTemplateWhenRequired():
    result = _Evaluate({"is_template": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's template status is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An absent 'is_template' key is treated as False, so it satisfies a requirement of False.
def test_MissingStatus():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_MissingStatusWhenRequired():
    result = _Evaluate({}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's template status is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_Skip():
    result = TemplateRequirement().Evaluate({}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
