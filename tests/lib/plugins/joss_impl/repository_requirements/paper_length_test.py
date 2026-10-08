import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_length import (
    PaperLengthRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PaperLengthRequirement()

    assert requirement.name == "PaperLength"
    assert (
        requirement.description
        == "Validates that the number of words in the paper is within the range that JOSS recommends."
    )
    assert requirement.requires_explicit_include is False

    parameters = requirement.GetParameters()

    assert parameters["minimum"].default == 750  # noqa: PLR2004
    assert parameters["maximum"].default == 1750  # noqa: PLR2004


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("words", "expected_result", "expected_context"),
    [
        (10, EvaluateResultValue.Success, "`paper/paper.md` contains 10 words."),
        (20, EvaluateResultValue.Success, "`paper/paper.md` contains 20 words."),
        (9, EvaluateResultValue.Error, "`paper/paper.md` contains 9 words, but at least 10 are required."),
        (21, EvaluateResultValue.Error, "`paper/paper.md` contains 21 words, but at most 20 are allowed."),
    ],
)
def test_Evaluate(words, expected_result, expected_context):
    result = PaperLengthRequirement().Evaluate(
        JOSSModule(),
        {"paper": Paper("paper/paper.md", " ".join(["word"] * words), {}, None)},
        {"skip": False, "minimum": 10, "maximum": 20},
    )

    assert result.result == expected_result
    assert result.context == expected_context
    assert (result.resolution is None) is (expected_result == EvaluateResultValue.Success)
    assert result.rationale is None
