from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.ruleset_requirements.require_linear_history import (
    RequireLinearHistoryRequirement,
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
