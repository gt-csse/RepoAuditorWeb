import pytest

from RepoAuditorWeb.lib.plugins.github_impl.web_commit_signoff_requirement import (
    WebCommitSignoffRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue


# ----------------------------------------------------------------------
def _Evaluate(response: dict, *, no: bool = False) -> EvaluateResult:
    return WebCommitSignoffRequirement().Evaluate({"response": response}, {"skip": False, "no": no})


# ----------------------------------------------------------------------
def test_Construct():
    requirement = WebCommitSignoffRequirement()

    assert requirement.name == "WebCommitSignoff"
    assert requirement.description == "Requirement to validate a repository's web commit signoff status."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = WebCommitSignoffRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "no"]
    assert parameters["no"].type is bool
    assert parameters["no"].default is False


# ----------------------------------------------------------------------
# 'no' inverts the expected value, so signoff is required by default.
@pytest.mark.parametrize(
    ("web_commit_signoff_required", "no"),
    [(True, False), (False, True)],
)
def test_MatchingValue(web_commit_signoff_required, no):
    result = _Evaluate({"web_commit_signoff_required": web_commit_signoff_required}, no=no)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_SignoffNotEnabledWhenRequired():
    result = _Evaluate({"web_commit_signoff_required": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's web commit signoff value is 'False', but the requirement specifies it must be"
        " 'True'."
    )


# ----------------------------------------------------------------------
def test_SignoffEnabledWhenNotRequired():
    result = _Evaluate({"web_commit_signoff_required": True}, no=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's web commit signoff value is 'True', but the requirement specifies it must be"
        " 'False'."
    )


# ----------------------------------------------------------------------
# An absent key is treated as False, so it fails when signoff is required.
def test_MissingValue():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's web commit signoff value is 'False', but the requirement specifies it must be"
        " 'True'."
    )


# ----------------------------------------------------------------------
def test_MissingValueWhenNotRequired():
    result = _Evaluate({}, no=True)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_Skip():
    result = WebCommitSignoffRequirement().Evaluate({}, {"skip": True, "no": False})

    assert result.result == EvaluateResultValue.Skipped
