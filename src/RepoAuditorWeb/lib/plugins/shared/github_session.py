from urllib.parse import urlparse

import requests

from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# ----------------------------------------------------------------------
class GitHubSession(requests.Session):
    """Session used to communicate with GitHub APIs."""

    # requests waits indefinitely by default, which would stall the audit on an unresponsive server.
    TIMEOUT_SECONDS = 30

    # ----------------------------------------------------------------------
    def __init__(
        self,
        github_url: str,
        github_pat: str | None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        # Rate limiting and server errors are often transient.
        adapter = HTTPAdapter(
            max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]),
        )

        self.mount("https://", adapter)
        self.mount("http://", adapter)

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

        kwargs.setdefault("timeout", self.TIMEOUT_SECONDS)

        return super().request(
            method,
            f"{self.api_url}{url}",
            *args,
            **kwargs,
        )
