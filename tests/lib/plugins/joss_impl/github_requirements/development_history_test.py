from datetime import datetime, UTC

import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements import minimum_months_requirement
from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.development_history import (
    DevelopmentHistoryRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Recent():
    today = datetime.now(UTC)

    result = DevelopmentHistoryRequirement().Evaluate(
        JOSSModule(),
        {"first_commit_date": today},
        {"skip": False, "months": 6},
    )

    assert result.result == EvaluateResultValue.Error
    assert (
        result.context
        == f"The first commit was authored on {today.date().isoformat()}, 0 full month(s) ago, but at least 6 are required."
    )
    assert result.resolution is not None
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_OverriddenMonths():
    today = datetime.now(UTC)

    result = DevelopmentHistoryRequirement().Evaluate(
        JOSSModule(),
        {"first_commit_date": today},
        {"skip": False, "months": 0},
    )

    assert result.result == EvaluateResultValue.Success
    assert (
        result.context == f"The first commit was authored on {today.date().isoformat()}, 0 full month(s) ago."
    )
    assert result.rationale is None


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("now", "date", "expected_context"),
    [
        (
            datetime(2026, 7, 15, tzinfo=UTC),
            datetime(2026, 1, 15, tzinfo=UTC),
            "The first commit was authored on 2026-01-15, 6 full month(s) ago.",
        ),
        (
            datetime(2026, 7, 15, tzinfo=UTC),
            datetime(2026, 1, 16, tzinfo=UTC),
            "The first commit was authored on 2026-01-16, 5 full month(s) ago, but at least 6 are required.",
        ),
        # The 31st has no counterpart in a 30-day month.
        (
            datetime(2026, 3, 31, tzinfo=UTC),
            datetime(2025, 9, 30, tzinfo=UTC),
            "The first commit was authored on 2025-09-30, 6 full month(s) ago.",
        ),
        (
            datetime(2026, 3, 31, tzinfo=UTC),
            datetime(2025, 10, 1, tzinfo=UTC),
            "The first commit was authored on 2025-10-01, 5 full month(s) ago, but at least 6 are required.",
        ),
    ],
)
def test_FullMonths(monkeypatch, now, date, expected_context):
    # ----------------------------------------------------------------------
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return now

    # ----------------------------------------------------------------------

    monkeypatch.setattr(minimum_months_requirement, "datetime", FixedDatetime)

    result = DevelopmentHistoryRequirement().Evaluate(
        JOSSModule(),
        {"first_commit_date": date},
        {"skip": False, "months": 6},
    )

    assert result.context == expected_context
