from typing import cast, override
from urllib.parse import quote

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

            # The branch is a path segment; characters that git permits (such as '#') would otherwise
            # end the path.
            encoded_branch = quote(branch)

            # Get the classic branch protection data for the branch
            response = session.get(f"branches/{encoded_branch}")

            response.raise_for_status()
            response = response.json()

            if not response.get("protected", False):
                return None

            # Note that once here, we know that the branch is protected, but we don't know the
            # protection scheme used (rule sets or classic). Attempt to get the classic information
            # and then see if rule sets are in use if the classic information is not found.
            response = session.get(f"branches/{encoded_branch}/protection")

            # GitHub reports classic protection only to callers with administrative access, so whether a
            # classic rule is in use is unknown; the requirement reports that rather than an error.
            if response.status_code in (requests.codes.UNAUTHORIZED, requests.codes.FORBIDDEN):
                module_data["branch"] = branch
                module_data["response"] = None

                return module_data

            if response.status_code == requests.codes.NOT_FOUND:
                # Does this branch use rule sets?
                ruleset_response = session.get(f"rules/branches/{encoded_branch}")

                ruleset_response.raise_for_status()
                ruleset_response = ruleset_response.json()

                # If there is data, assume that the branch is protected by rule sets
                if ruleset_response:
                    return None

                # If here, let the error result in an exception in the code that follows.

            response.raise_for_status()
            response = response.json()

            module_data["branch"] = branch
            module_data["response"] = response

            return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass  # No cleanup necessary
