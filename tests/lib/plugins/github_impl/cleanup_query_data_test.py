import pytest

from RepoAuditorWeb.lib.plugins.github_impl.classic_branch_protection_query import (
    ClassicBranchProtectionQuery,
)
from RepoAuditorWeb.lib.plugins.github_impl.default_branch_query import DefaultBranchQuery
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_query import RulesetQuery
from RepoAuditorWeb.lib.plugins.github_impl.standard_query import StandardQuery


# ----------------------------------------------------------------------
# GitHub queries only hold API responses, so there is nothing to release and the data must be left intact.
@pytest.mark.parametrize(
    "query_type",
    [ClassicBranchProtectionQuery, DefaultBranchQuery, RulesetQuery, StandardQuery],
)
def test_CleanupQueryDataPreservesData(query_type):
    response: dict[str, object] = {"description": "My description."}
    query_data: dict[str, object] = {"response": response, "branch": "main"}

    query_type().CleanupQueryData(query_data)

    assert query_data == {"response": {"description": "My description."}, "branch": "main"}
    assert query_data["response"] is response
