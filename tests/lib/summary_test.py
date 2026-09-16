from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue
from RepoAuditorWeb.lib.summary import RESULT_VALUE_NAMES, Summary

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateResult(result: EvaluateResultValue = EvaluateResultValue.Error) -> EvaluateResult:
    requirement = MyRequirement("MyRequirement", "My requirement description.")
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])

    return EvaluateResult(result, None, None, None, requirement, module)


# ----------------------------------------------------------------------
class TestCreate:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        summary = Summary.Create([])

        assert summary == Summary()
        assert summary.total == 0

    # ----------------------------------------------------------------------
    def test_Counts(self):
        summary = Summary.Create(
            [
                _CreateResult(EvaluateResultValue.Skipped),
                _CreateResult(EvaluateResultValue.DoesNotApply),
                _CreateResult(EvaluateResultValue.Success),
                _CreateResult(EvaluateResultValue.Success),
                _CreateResult(EvaluateResultValue.Warning),
                _CreateResult(EvaluateResultValue.Error),
            ],
        )

        assert summary == Summary(skipped=1, does_not_apply=1, success=2, warning=1, error=1)
        assert summary.total == 6


# ----------------------------------------------------------------------
class TestCalcPercentage:
    # ----------------------------------------------------------------------
    def test_Standard(self):
        assert Summary.Create([_CreateResult()] * 4).CalcPercentage(1) == "25.00%"

    # ----------------------------------------------------------------------
    # Nothing was tallied, so there is no total to divide by.
    def test_WithoutResults(self):
        assert Summary().CalcPercentage(0) == "0.00%"


# ----------------------------------------------------------------------
# The names identify a result value in every experience that reports results, so they must match the
# fields that they are tallied into.
def test_ResultValueNamesMatchSummaryFields():
    assert set(RESULT_VALUE_NAMES.values()) == {
        "skipped",
        "does_not_apply",
        "success",
        "warning",
        "error",
    }

    for name in RESULT_VALUE_NAMES.values():
        assert hasattr(Summary(), name)
