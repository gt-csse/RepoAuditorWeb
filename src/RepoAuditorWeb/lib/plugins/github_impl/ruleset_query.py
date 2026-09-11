from typing import cast, override

import requests

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
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_creations import (
    RestrictCreationsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_deletions import (
    RestrictDeletionsRequirement,
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
                RestrictDeletionsRequirement(),
                RestrictCreationsRequirement(),
                RestrictUpdatesRequirement(),
                RequireLinearHistoryRequirement(),
                RequireSuccessfulDeploymentsRequirement(),
                RequireSignedCommitsRequirement(),
                RequirePullRequestsRequirement(),
                RequireApprovalsRequirement(),
                DismissStalePullRequestApprovalsRequirement(),
                RequireReviewFromCodeOwnersRequirement(),
                RequireApprovalOfMostRecentPushRequirement(),
                RequireConversationResolutionRequirement(),
                RequireStatusChecksToPassRequirement(),
                RequireBranchesToBeUpToDateBeforeMergingRequirement(),
                BlockForcePushesRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        # Get the branch
        branch = module_data["branch"]
        if branch is None:
            # Get the default branch name
            response = cast(requests.Session, module_data["session"]).get("")

            response.raise_for_status()
            response = response.json()

            branch = response["default_branch"]

        # Get the ruleset data for the branch
        response = cast(requests.Session, module_data["session"]).get(f"rules/branches/{branch}")

        response.raise_for_status()
        response = response.json()

        if not response:
            return None

        module_data["branch"] = branch
        module_data["response"] = response

        return module_data
