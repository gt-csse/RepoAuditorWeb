from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.allow_auto_merge import (
    AllowAutoMergeRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.allow_merge_commits import (
    AllowMergeCommitsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.allow_rebase_merging import (
    AllowRebaseMergingRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.allow_squash_merging import (
    AllowSquashMergingRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.always_suggest_updating_pull_request_branches import (
    AlwaysSuggestUpdatingPullRequestBranchesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.automatically_delete_head_branches import (
    AutomaticallyDeleteHeadBranchesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.default_branch import (
    DefaultBranchRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.dependabot_security_updates import (
    DependabotSecurityUpdatesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.description import DescriptionRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.discussions import (
    DiscussionsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.issues import (
    IssuesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.license import LicenseRequirement
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.merge_commit_message import (
    MergeCommitMessageRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.projects import (
    ProjectsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.pull_requests import (
    PullRequestsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.push_protection import (
    PushProtectionRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.repository_visibility import (
    RepositoryVisibilityRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.require_contributors_to_sign_off_on_web_based_commits import (
    RequireContributorsToSignOffOnWebBasedCommitsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.secret_protection import (
    SecretProtectionRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.squash_commit_message import (
    SquashCommitMessageRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.template_repository import (
    TemplateRepositoryRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.wikis import (
    WikisRequirement,
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
                TemplateRepositoryRequirement(),
                DefaultBranchRequirement(),
                # settings page (Features)
                WikisRequirement(),
                IssuesRequirement(),
                DiscussionsRequirement(),
                ProjectsRequirement(),
                PullRequestsRequirement(),
                # settings page (Pull Requests)
                AllowMergeCommitsRequirement(),
                MergeCommitMessageRequirement(),
                AllowSquashMergingRequirement(),
                SquashCommitMessageRequirement(),
                AllowRebaseMergingRequirement(),
                AlwaysSuggestUpdatingPullRequestBranchesRequirement(),
                AllowAutoMergeRequirement(),
                AutomaticallyDeleteHeadBranchesRequirement(),
                # settings page (Commits)
                RequireContributorsToSignOffOnWebBasedCommitsRequirement(),
                # settings page (Danger Zone)
                RepositoryVisibilityRequirement(),
                # advanced security page
                DependabotSecurityUpdatesRequirement(),
                SecretProtectionRequirement(),
                PushProtectionRequirement(),
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

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass  # No cleanup necessary
