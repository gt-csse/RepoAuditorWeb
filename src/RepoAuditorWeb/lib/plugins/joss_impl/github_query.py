from datetime import datetime
from typing import cast, override
from urllib.parse import parse_qs, urlparse

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.contributors import ContributorsRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.development_history import (
    DevelopmentHistoryRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.issues import IssuesRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.license import LicenseRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.public_history import (
    PublicHistoryRequirement,
)
from RepoAuditorWeb.lib.plugins.shared.github_session import GitHubSession
from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class GitHubQuery(Query):
    """Query with requirements that evaluate the repository's license, history, and contributors using the GitHub API."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "GitHub",
            [
                LicenseRequirement(),
                PublicHistoryRequirement(),
                DevelopmentHistoryRequirement(),
                ContributorsRequirement(),
                IssuesRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        with GitHubSession(cast(str, module_data["url"]), cast(str | None, module_data["pat"])) as session:
            response = session.get("")
            response.raise_for_status()

            repository = response.json()

            # Commits are listed newest first, so the last page of a single commit per page holds the first commit.
            commit_params: dict[str, str | int] = {
                "sha": cast(str | None, module_data["branch"]) or repository["default_branch"],
                "per_page": 1,
            }

            response = session.get("commits", params=commit_params)
            response.raise_for_status()

            last_link = response.links.get("last")

            if last_link is not None:
                response = session.get(
                    "commits",
                    params={**commit_params, "page": parse_qs(urlparse(last_link["url"]).query)["page"][0]},
                )
                response.raise_for_status()

            first_commit_date = datetime.fromisoformat(response.json()[-1]["commit"]["author"]["date"])

            # All pages are retrieved so that any minimum can be evaluated; GitHub lists at most 500
            # contributors that are associated with an account, which bounds the number of requests.
            contributors: list[str] = []
            page = 1

            while True:
                response = session.get("contributors", params={"per_page": 100, "page": page})
                response.raise_for_status()

                contributors += [
                    contributor["login"]
                    for contributor in response.json()
                    if contributor.get("type") != "Bot"
                ]

                if "next" not in response.links:
                    break

                page += 1

            module_data["repository"] = repository
            module_data["first_commit_date"] = first_commit_date
            module_data["contributors"] = contributors

        return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass  # No cleanup necessary
