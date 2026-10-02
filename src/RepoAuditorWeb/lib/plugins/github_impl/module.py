from typing import override
from urllib.parse import urlparse

import requests

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.github_impl.classic_branch_protection_query import (
    ClassicBranchProtectionQuery,
)
from RepoAuditorWeb.lib.plugins.github_impl.default_branch_query import DefaultBranchQuery
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_query import RulesetQuery
from RepoAuditorWeb.lib.plugins.github_impl.standard_query import StandardQuery
from RepoAuditorWeb.lib.plugins.github_impl.team_size import TeamSize
from RepoAuditorWeb.lib.plugins.shared.repository_arguments import (
    GetRepositoryParameters,
    ResolveRepositoryArguments,
)


# ----------------------------------------------------------------------
class GitHubModule(Module):
    """Module for validating GitHub repository configuration settings."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "GitHub",
            "Validates GitHub configuration settings.",
            [
                StandardQuery(),
                DefaultBranchQuery(),
                RulesetQuery(),
                ClassicBranchProtectionQuery(),
            ],
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            **GetRepositoryParameters(),
            "team_size": TyperParameter(
                TeamSize,
                TeamSize.Small,
                OptionInfo(help=TeamSize.__doc__),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self,
        arguments: dict[str | None, dict[str, object]],
    ) -> dict[str | None, dict[str, object]]:
        module_data = arguments.get(None, {})
        repository_arguments = ResolveRepositoryArguments(module_data)

        arguments[None] = {
            "session": GitHubSession(repository_arguments.url, repository_arguments.pat),
            "branch": repository_arguments.branch,
            "team_size": TeamSize(module_data.get("team_size") or TeamSize.Small),
        }

        return arguments


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class GitHubSession(requests.Session):
    """Session used to communicate with GitHub APIs."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        github_url: str,
        github_pat: str | None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.headers.update(
            {
                "X-GitHub-Api-Version": "2022-11-28",
                "Accept": "application/vnd.github+json",
            },
        )

        if github_pat:
            self.headers["Authorization"] = f"Bearer {github_pat}"

        github_url = github_url.removesuffix("/")

        url_parts = urlparse(github_url)
        path_parts = url_parts.path.split("/")

        # The URL should be in the form <github_server>/<username>/<repository>
        if len(path_parts) != 3:  # noqa: PLR2004
            msg = f"'{github_url}' is not a valid GitHub repository URL."
            raise ValueError(msg)

        _, username, repo = path_parts

        if url_parts.netloc.lower() in {"github.com", "www.github.com"}:
            api_url = f"https://api.github.com/repos/{username}/{repo}"
            is_enterprise = False
        else:
            if not url_parts.netloc:
                msg = f"'{github_url}' is not a valid GitHub repository URL."
                raise ValueError(msg)

            api_url = f"{url_parts.scheme or 'https'}://{url_parts.netloc}/api/v3/repos/{username}/{repo}"
            is_enterprise = True

        self.github_url = github_url
        self.github_pat = github_pat
        self.github_username = username
        self.github_repository = repo
        self.api_url = api_url
        self.is_enterprise = is_enterprise
        self.has_pat = bool(github_pat)

    # ----------------------------------------------------------------------
    def request(
        self,
        method: str,
        url: str,
        *args,
        **kwargs,
    ) -> requests.Response:
        """Invoke the request relative to the repository's API url."""

        if url and not url.startswith("/"):
            url = f"/{url}"

        return super().request(
            method,
            f"{self.api_url}{url}",
            *args,
            **kwargs,
        )
