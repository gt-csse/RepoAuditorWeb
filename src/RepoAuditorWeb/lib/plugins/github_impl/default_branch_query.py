from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.default_branch_requirements.protected_mainline_branch import (
    ProtectedMainlineBranchRequirement,
)
from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class DefaultBranchQuery(Query):
    """Query with Requirements that operated on the GitHub's default branch protection."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "DefaultBranch",
            [
                ProtectedMainlineBranchRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        # Get the default branch name
        response = cast(requests.Session, module_data["session"]).get("")

        response.raise_for_status()
        response = response.json()

        module_data["default_branch"] = response["default_branch"]

        # Get the information associated with the default branch
        response = cast(requests.Session, module_data["session"]).get(
            f"branches/{module_data['default_branch']}"
        )

        response.raise_for_status()
        response = response.json()

        module_data["response"] = response

        return module_data
