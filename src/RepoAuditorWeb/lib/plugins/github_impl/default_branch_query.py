from typing import cast, override
from urllib.parse import quote

import requests

from RepoAuditorWeb.lib.plugins.github_impl.default_branch_requirements.protected_default_branch import (
    ProtectedDefaultBranchRequirement,
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
                ProtectedDefaultBranchRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        # The session is shared by the module's queries and remains usable once closed; closing it
        # releases its pooled connections, as Module provides no cleanup hook.
        with cast(requests.Session, module_data["session"]) as session:
            # Get the default branch name
            response = session.get("")

            response.raise_for_status()
            response = response.json()

            module_data["default_branch"] = response["default_branch"]

            # Get the information associated with the default branch. The branch is a path segment;
            # characters that git permits (such as '#') would otherwise end the path.
            response = session.get(f"branches/{quote(module_data['default_branch'])}")

            response.raise_for_status()
            response = response.json()

            module_data["response"] = response

            return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass  # No cleanup necessary
