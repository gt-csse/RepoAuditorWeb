from pathlib import Path
from typing import override
from urllib.parse import urlparse

import requests

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.github_impl.standard_query import StandardQuery


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
            ],
            requires_explicit_include=False,  # TODO: True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "url": TyperParameter(
                str,
                None,
                OptionInfo(help="[REQUIRED] GitHub  URL (e.g. https://github.com/gt-csse/RepoAuditorWeb)."),
            ),
            "pat": TyperParameter(
                str | None,
                None,
                OptionInfo(
                    help="GitHub Personal Access Token (PAT) or path to a local file containing the PAT.",
                    envvar="REPO_AUDITOR_WEB_GITHUB_PAT",
                ),
            ),
            "branch": TyperParameter(
                str | None,
                None,
                OptionInfo(help="Branch to evaluate. The default branch will be used if not specified."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self,
        arguments: dict[str | None, dict[str, object]],
    ) -> dict[str | None, dict[str, object]]:
        module_data = arguments.get(None, {})

        # Get the URL
        url = module_data.get("url")

        if url is None:
            msg = "'url' is required argument for this module."
            raise ValueError(msg)

        assert isinstance(url, str), (url, type(url))

        # Get the PAT
        github_pat = module_data.get("pat")
        if github_pat is not None:
            assert isinstance(github_pat, str), (github_pat, type(github_pat))

            potential_filename = Path(github_pat)
            if potential_filename.is_file():
                with potential_filename.open(encoding="utf-8") as f:
                    github_pat = f.read().strip()

        arguments[None] = {
            "session": GitHubSession(url, github_pat),
            "branch": module_data["branch"],
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
