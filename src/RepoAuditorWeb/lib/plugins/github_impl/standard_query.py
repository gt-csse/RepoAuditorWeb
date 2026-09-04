from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.auto_merge import AutoMergeRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.default_branch import (
    DefaultBranchRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.delete_branch_on_merge import (
    DeleteBranchOnMergeRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.description import DescriptionRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.license import LicenseRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.merge_commit_message import (
    MergeCommitMessageRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.merge_commit import MergeCommitRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.rebase_commit import (
    RebaseCommitRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.squash_commit_message import (
    SquashCommitMessageRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.squash_commit import (
    SquashCommitRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.suggest_updating_pull_request_branches import (
    SuggestUpdatingPullRequestBranchesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_discussions import (
    SupportDiscussionsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_issues import (
    SupportIssuesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_projects import (
    SupportProjectsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_pull_requests import (
    SupportPullRequestsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.support_wikis import (
    SupportWikisRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.template import TemplateRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.web_commit_signoff import (
    WebCommitSignoffRequirement,
)
from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class StandardQuery(Query):
    """Query with Requirements that operate on basic GitHub repository data."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Standard",
            [
                # metadata
                DescriptionRequirement(),
                LicenseRequirement(),
                # settings page
                TemplateRequirement(),
                WebCommitSignoffRequirement(),
                DefaultBranchRequirement(),
                # settings page (Features)
                SupportWikisRequirement(),
                SupportIssuesRequirement(),
                SupportDiscussionsRequirement(),
                SupportProjectsRequirement(),
                SupportPullRequestsRequirement(),
                # settings page (Pull Requests)
                MergeCommitRequirement(),
                MergeCommitMessageRequirement(),
                SquashCommitRequirement(),
                SquashCommitMessageRequirement(),
                RebaseCommitRequirement(),
                SuggestUpdatingPullRequestBranchesRequirement(),
                AutoMergeRequirement(),
                DeleteBranchOnMergeRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        response = cast(requests.Session, module_data["session"]).get("")

        response.raise_for_status()
        response = response.json()

        module_data["response"] = response
        return module_data
