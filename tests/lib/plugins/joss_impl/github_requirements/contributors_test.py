import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.contributors import ContributorsRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("contributors", "minimum", "expected_result", "expected_context"),
    [
        (["one", "two"], 2, EvaluateResultValue.Success, "2 contributor(s) were found."),
        (["one"] * 150, 150, EvaluateResultValue.Success, "150 contributor(s) were found."),
        (["one"], 2, EvaluateResultValue.Error, "1 contributor(s) were found, but at least 2 are required."),
        ([], 1, EvaluateResultValue.Error, "0 contributor(s) were found, but at least 1 are required."),
    ],
)
def test_Evaluate(contributors, minimum, expected_result, expected_context):
    result = ContributorsRequirement().Evaluate(
        JOSSModule(),
        {"contributors": contributors},
        {"skip": False, "minimum": minimum},
    )

    assert result.result == expected_result
    assert result.context == expected_context
    assert (result.resolution is None) is (expected_result == EvaluateResultValue.Success)
    assert (result.rationale is None) is (minimum != 2)  # noqa: PLR2004
