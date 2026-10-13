import re

from urllib.parse import urlparse

import requests

from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# ----------------------------------------------------------------------
def GetApiBaseUrl(scheme: str, netloc: str) -> str:
    """Return the base url of the REST API exposed by the GitHub server at netloc."""

    if netloc.lower() in {"github.com", "www.github.com"}:
        return _PUBLIC_API_URL

    # Enterprise instances expose the API under a /api/v3 path on the same host.
    return f"{scheme}://{netloc}/api/v3"


# ----------------------------------------------------------------------
class GitHubApiSession(requests.Session):
    """Session used to communicate with GitHub APIs relative to a base API url."""

    # requests waits indefinitely by default, which would stall the audit on an unresponsive server.
    TIMEOUT_SECONDS = 30

    # ----------------------------------------------------------------------
    def __init__(
        self,
        api_url: str,
        github_pat: str | None,
        *args,
        **kwargs,
    ) -> None:
        # Request urls are appended to the api url, which would otherwise produce '//' in their paths.
        url_parts = urlparse(api_url)
        url_parts = url_parts._replace(path=url_parts.path.rstrip("/"))

        # As with the clone, the PAT is never sent over an unencrypted connection. This is enforced
        # here, where the PAT is attached, so that no caller can pair a PAT with an unencrypted url.
        if github_pat:
            url_parts = url_parts._replace(scheme="https")

        # A query or fragment would precede the request urls appended to the api url.
        if (
            url_parts.scheme not in ("https", "http")
            or not url_parts.netloc
            or url_parts.params
            or url_parts.query
            or url_parts.fragment
        ):
            msg = f"'{api_url}' is not a valid GitHub API URL."
            raise ValueError(msg)

        api_url = url_parts.geturl()

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

        self.api_url = api_url
        self.github_pat = github_pat
        self.has_pat = bool(github_pat)

    # ----------------------------------------------------------------------
    def request(
        self,
        method: str,
        url: str,
        *args,
        **kwargs,
    ) -> requests.Response:
        """Invoke the request relative to the API url."""

        if url and not url.startswith("/"):
            url = f"/{url}"

        kwargs.setdefault("timeout", self.TIMEOUT_SECONDS)

        return super().request(
            method,
            f"{self.api_url}{url}",
            *args,
            **kwargs,
        )


# ----------------------------------------------------------------------
class GitHubSession(GitHubApiSession):
    """Session used to communicate with the GitHub APIs of a single repository."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        github_url: str,
        github_pat: str | None,
        *args,
        **kwargs,
    ) -> None:
        github_url = github_url.removesuffix("/")

        url_parts = urlparse(github_url)
        path_parts = url_parts.path.split("/")

        # The URL should be in the form <github_server>/<username>/<repository>. The names are placed
        # in API paths, where segments such as '..' would change the resource requested. GitHub is
        # only reached over http(s), so a url with another scheme (or without a host) does not
        # identify a repository that can be queried.
        if (
            len(path_parts) != 3  # noqa: PLR2004
            or not all(_NAME_REGEX.match(part) for part in path_parts[1:])
            or url_parts.scheme not in ("https", "http")
            or not url_parts.netloc
        ):
            msg = f"'{github_url}' is not a valid GitHub repository URL."
            raise ValueError(msg)

        _, username, repo = path_parts

        api_base_url = GetApiBaseUrl(url_parts.scheme, url_parts.netloc)

        super().__init__(f"{api_base_url}/repos/{username}/{repo}", github_pat, *args, **kwargs)

        self.github_url = github_url
        self.github_username = username
        self.github_repository = repo
        self.is_enterprise = api_base_url != _PUBLIC_API_URL


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_PUBLIC_API_URL = "https://api.github.com"

# The characters GitHub permits in user, organization, and repository names, excluding '.' and '..'.
_NAME_REGEX = re.compile(r"^(?!\.\.?$)[A-Za-z0-9_.-]+$")
