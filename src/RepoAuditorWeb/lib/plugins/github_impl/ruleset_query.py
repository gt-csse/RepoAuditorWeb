from typing import cast, override
from urllib.parse import quote

import requests

from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.allowed_merge_methods import (
    AllowedMergeMethodsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.block_force_pushes import (
    BlockForcePushesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.dismiss_stale_pull_request_approvals import (
    DismissStalePullRequestApprovalsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_approval_of_most_recent_push import (
    RequireApprovalOfMostRecentPushRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_approvals import (
    RequireApprovalsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_branches_to_be_up_to_date_before_merging import (
    RequireBranchesToBeUpToDateBeforeMergingRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_code_scanning_results import (
    RequireCodeScanningResultsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_conversation_resolution import (
    RequireConversationResolutionRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_linear_history import (
    RequireLinearHistoryRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_pull_requests import (
    RequirePullRequestsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_review_from_code_owners import (
    RequireReviewFromCodeOwnersRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_signed_commits import (
    RequireSignedCommitsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_status_checks_to_pass import (
    RequireStatusChecksToPassRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_successful_deployments import (
    RequireSuccessfulDeploymentsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.required_reviewers import (
    RequiredReviewersRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_creations import (
    RestrictCreationsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_deletions import (
    RestrictDeletionsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_dismiss_pull_request_reviews import (
    RestrictDismissPullRequestReviewsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_updates import (
    RestrictUpdatesRequirement,
)
from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class RulesetQuery(Query):
    """Query to validate GitHub repository rulesets."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RulesetQuery",
            [
                # branch rules
                RestrictCreationsRequirement(),
                RestrictUpdatesRequirement(),
                RestrictDeletionsRequirement(),
                RequireLinearHistoryRequirement(),
                RequireSuccessfulDeploymentsRequirement(),
                RequireSignedCommitsRequirement(),
                # branch rules (Require a pull request before merging)
                RequirePullRequestsRequirement(),
                RequireApprovalsRequirement(),
                DismissStalePullRequestApprovalsRequirement(),
                RequireReviewFromCodeOwnersRequirement(),
                RequireApprovalOfMostRecentPushRequirement(),
                RestrictDismissPullRequestReviewsRequirement(),
                RequiredReviewersRequirement(),
                RequireConversationResolutionRequirement(),
                AllowedMergeMethodsRequirement(),
                # branch rules (continued)
                RequireStatusChecksToPassRequirement(),
                RequireBranchesToBeUpToDateBeforeMergingRequirement(),
                BlockForcePushesRequirement(),
                RequireCodeScanningResultsRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        # The session is shared by the module's queries and remains usable once closed; closing it
        # releases its pooled connections, as Module provides no cleanup hook.
        with cast(requests.Session, module_data["session"]) as session:
            # Get the branch
            branch = module_data["branch"]
            if branch is None:
                # Get the default branch name
                response = session.get("")

                response.raise_for_status()
                response = response.json()

                branch = response["default_branch"]

            assert isinstance(branch, str), (branch, type(branch))

            # Get the ruleset data for the branch. The branch is a path segment; characters that git
            # permits (such as '#') would otherwise end the path.
            response = session.get(f"rules/branches/{quote(branch)}")

            response.raise_for_status()
            response = response.json()

            if not response:
                return None

            module_data["branch"] = branch
            module_data["response"] = response

            return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass  # No cleanup necessary
