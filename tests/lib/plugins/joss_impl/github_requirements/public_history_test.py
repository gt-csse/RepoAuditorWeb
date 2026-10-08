import textwrap

from datetime import datetime, UTC

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.public_history import (
    PublicHistoryRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Private():
    result = PublicHistoryRequirement().Evaluate(
        JOSSModule(),
        {
            "repository": {
                "private": True,
                "html_url": "https://github.com/owner/repo",
                "created_at": "2000-01-01T00:00:00Z",
            },
        },
        {"skip": False, "months": 6},
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The repository is private."
    assert result.resolution is not None
    assert "(https://github.com/owner/repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_Recent():
    today = datetime.now(UTC)

    result = PublicHistoryRequirement().Evaluate(
        JOSSModule(),
        {"repository": {"private": False, "created_at": today.isoformat()}},
        {"skip": False, "months": 6},
    )

    assert result.result == EvaluateResultValue.Error
    assert (
        result.context
        == f"The repository was created on {today.date().isoformat()}, 0 full month(s) ago, but at least 6 are required."
    )
    assert result.resolution == textwrap.dedent(
        """\
        Continue developing the software in the public repository until it has been public for
        the required period, then submit it to JOSS.
        """,
    )
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_Old():
    result = PublicHistoryRequirement().Evaluate(
        JOSSModule(),
        {"repository": {"private": False, "created_at": "2000-01-15T00:00:00Z"}},
        {"skip": False, "months": 6},
    )

    now = datetime.now(UTC)
    elapsed = (now.year - 2000) * 12 + now.month - 1 - (now.day < 15)  # noqa: PLR2004

    assert result.result == EvaluateResultValue.Success
    assert result.context == f"The repository was created on 2000-01-15, {elapsed} full month(s) ago."
    assert result.resolution is None
    assert result.rationale is not None
