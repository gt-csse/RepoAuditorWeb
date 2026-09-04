from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.auto_merge_requirement import AutoMergeRequirement
from RepoAuditorWeb.lib.plugins.github_impl.default_branch_requirement import DefaultBranchRequirement
from RepoAuditorWeb.lib.plugins.github_impl.description_requirement import DescriptionRequirement
from RepoAuditorWeb.lib.plugins.github_impl.license_requirement import LicenseRequirement
from RepoAuditorWeb.lib.plugins.github_impl.merge_commit_message_requirement import (
    MergeCommitMessageRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.merge_commit_requirement import MergeCommitRequirement
from RepoAuditorWeb.lib.plugins.github_impl.rebase_commit_requirement import RebaseCommitRequirement
from RepoAuditorWeb.lib.plugins.github_impl.squash_commit_message_requirement import (
    SquashCommitMessageRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.squash_commit_requirement import SquashCommitRequirement
from RepoAuditorWeb.lib.plugins.github_impl.suggest_updating_pull_request_branches_requirement import (
    SuggestUpdatingPullRequestBranchesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.support_discussions_requirement import (
    SupportDiscussionsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.support_issues_requirement import SupportIssuesRequirement
from RepoAuditorWeb.lib.plugins.github_impl.support_projects_requirement import (
    SupportProjectsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.support_pull_requests_requirement import (
    SupportPullRequestsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.support_wikis_requirement import SupportWikisRequirement
from RepoAuditorWeb.lib.plugins.github_impl.template_requirement import TemplateRequirement
from RepoAuditorWeb.lib.plugins.github_impl.web_commit_signoff_requirement import WebCommitSignoffRequirement
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
