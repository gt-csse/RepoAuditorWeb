from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.classic_branch_protection_requirements.ensure_not_used import (
    EnsureNotUsedRequirement,
)
from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class ClassicBranchProtectionQuery(Query):
    """Query to validate GitHub repository classic branch protection rules."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "ClassicBranchProtectionQuery",
            [
                EnsureNotUsedRequirement(),
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

        # Get the classic branch protection data for the branch
        response = cast(requests.Session, module_data["session"]).get(f"branches/{branch}")

        response.raise_for_status()
        response = response.json()

        if not response.get("protected", False):
            return None

        # Note that once here, we know that the branch is protected, but we don't know the
        # protection scheme used (rule sets or classic). Attempt to get the classic information
        # and then see if rule sets are in use if the classic information is not found.
        response = cast(requests.Session, module_data["session"]).get(f"/branches/{branch}/protection")

        if response.status_code == requests.codes.NOT_FOUND:
            # Does this branch use rule sets?
            ruleset_response = cast(requests.Session, module_data["session"]).get(f"rules/branches/{branch}")

            ruleset_response.raise_for_status()
            ruleset_response = ruleset_response.json()

            # If there is data, assume that the branch is protected by rule sets
            if ruleset_response:
                return None

            # If here, let the error result in an exception in the code that follows.

        response.raise_for_status()
        response = response.json()

        module_data["branch"] = branch
        module_data["branch_protection_data"] = response

        return module_data
