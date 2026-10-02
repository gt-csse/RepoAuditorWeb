import git

from RepoAuditorWeb.lib.plugins.community_standards_impl.community_standards_query import (
    CommunityStandardsQuery,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue

from conftest import MyModule


# ----------------------------------------------------------------------
def test_Construct():
    query = CommunityStandardsQuery()

    assert query.name == "Community Standards"
    assert [requirement.name for requirement in query.requirements] == [
        "Readme",
        "CodeOfConduct",
        "Contributing",
        "License",
        "Security",
        "IssueTemplate",
        "PullRequestTemplate",
    ]


# ----------------------------------------------------------------------
# Clones a real (local) repository so that the query and its requirements are exercised against
# the output of an actual git clone rather than a double.
def test_EndToEnd(tmp_path):
    source_dir = tmp_path / "source"
    source_repo = git.Repo.init(source_dir)

    (source_dir / "README.md").write_text("content", encoding="utf-8")
    (source_dir / "CODE_OF_CONDUCT.md").write_text("content", encoding="utf-8")
    (source_dir / "CONTRIBUTING.md").write_text("content", encoding="utf-8")
    (source_dir / "LICENSE").write_text("content", encoding="utf-8")
    (source_dir / ".github" / "ISSUE_TEMPLATE").mkdir(parents=True)
    (source_dir / ".github" / "ISSUE_TEMPLATE" / "bug_report.md").write_text("content", encoding="utf-8")
    (source_dir / ".github" / "pull_request_template.md").write_text("content", encoding="utf-8")
    (source_dir / "SECURITY.md").write_text("content", encoding="utf-8")
    source_repo.index.add(
        [
            "README.md",
            "CODE_OF_CONDUCT.md",
            "CONTRIBUTING.md",
            "LICENSE",
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/pull_request_template.md",
            "SECURITY.md",
        ],
    )
    source_repo.index.commit("Initial commit", author=git.Actor("Me", "me@example.com"))

    query = CommunityStandardsQuery()
    query_data = query.GetQueryData({"url": source_dir.as_uri(), "pat": None, "branch": None})

    assert query_data is not None

    try:
        module = MyModule("MyModule", "My description.", [query])
        results = [
            requirement.Evaluate(module, query_data, {"skip": False, "prohibit": False})
            for requirement in query.requirements
        ]
    finally:
        query.CleanupQueryData(query_data)

    assert [result.result for result in results] == [EvaluateResultValue.Success] * 7
