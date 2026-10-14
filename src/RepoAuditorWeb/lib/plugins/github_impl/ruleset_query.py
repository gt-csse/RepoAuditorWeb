from typing import cast, override
from urllib.parse import quote

import requests

from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.allowed_merge_methods import (
    AllowedMergeMethodsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.block_force_pushes import (
    BlockForcePushesRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.dismiss_stale_pull_request_approvals_when_new_commits_are_pushed import (
    DismissStalePullRequestApprovalsWhenNewCommitsArePushedRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_a_pull_request_before_merging import (
    RequireAPullRequestBeforeMergingRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_approval_of_the_most_recent_reviewable_push import (
    RequireApprovalOfTheMostRecentReviewablePushRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_branches_to_be_up_to_date_before_merging import (
    RequireBranchesToBeUpToDateBeforeMergingRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_code_scanning_results import (
    RequireCodeScanningResultsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_conversation_resolution_before_merging import (
    RequireConversationResolutionBeforeMergingRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_deployments_to_succeed import (
    RequireDeploymentsToSucceedRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_linear_history import (
    RequireLinearHistoryRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_review_from_code_owners import (
    RequireReviewFromCodeOwnersRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_review_from_specific_teams import (
    RequireReviewFromSpecificTeamsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_signed_commits import (
    RequireSignedCommitsRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_status_checks_to_pass import (
    RequireStatusChecksToPassRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.required_approvals import (
    RequiredApprovalsRequirement,
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
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.restrict_who_can_dismiss_pull_request_reviews import (
    RestrictWhoCanDismissPullRequestReviewsRequirement,
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
                RequireDeploymentsToSucceedRequirement(),
                RequireSignedCommitsRequirement(),
                # branch rules (Require a pull request before merging)
                RequireAPullRequestBeforeMergingRequirement(),
                RequiredApprovalsRequirement(),
                DismissStalePullRequestApprovalsWhenNewCommitsArePushedRequirement(),
                RequireReviewFromCodeOwnersRequirement(),
                RequireApprovalOfTheMostRecentReviewablePushRequirement(),
                RestrictWhoCanDismissPullRequestReviewsRequirement(),
                RequireReviewFromSpecificTeamsRequirement(),
                RequireConversationResolutionBeforeMergingRequirement(),
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
        session = cast(requests.Session, module_data["session"])

        repository = session.get("")

        repository.raise_for_status()
        repository = repository.json()

        # Get the branch
        branch = module_data["branch"]
        if branch is None:
            branch = repository["default_branch"]

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

        # Some ruleset settings are only offered on repositories owned by an organization.
        module_data["owner_type"] = repository["owner"]["type"]

        return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass  # No cleanup necessary
