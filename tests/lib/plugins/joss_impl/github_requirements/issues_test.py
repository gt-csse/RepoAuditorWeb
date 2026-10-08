from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.issues import IssuesRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_Enabled():
    result = IssuesRequirement().Evaluate(
        JOSSModule(),
        {"repository": {"has_issues": True, "html_url": "https://github.com/owner/repo"}},
        {"skip": False},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context == "Issues are enabled."
    assert result.resolution is None


# ----------------------------------------------------------------------
def test_Disabled():
    result = IssuesRequirement().Evaluate(
        JOSSModule(),
        {"repository": {"has_issues": False, "html_url": "https://github.com/owner/repo"}},
        {"skip": False},
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == "Issues are disabled."
    assert result.resolution is not None
    assert "(https://github.com/owner/repo/settings)" in result.resolution
    assert result.rationale is not None
