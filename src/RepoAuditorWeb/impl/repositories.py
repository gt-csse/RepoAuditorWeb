"""Resolves the repositories audited in a run, which may be every repository identified by a wildcard url."""

import copy

from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, urlparse, urlunparse
from urllib.request import url2pathname

from RepoAuditorWeb.lib.plugins.shared.github_session import GetApiBaseUrl, GitHubApiSession, NAME_REGEX
from RepoAuditorWeb.lib.plugins.shared.repository_arguments import ResolvePat

if TYPE_CHECKING:
    from collections.abc import Callable

    import requests

    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
WILDCARD = "*"


# ----------------------------------------------------------------------
def ResolveRepositories(
    dm: DoneManager,
    url: str | None,
    pat: str | None,
    *,
    include_archived: bool = False,
    include_forked: bool = False,
) -> list[str | None]:
    """Return the repositories identified by the url.

    A url without a wildcard identifies a single repository; no url is a single repository that is
    yet to be identified (for example, in the web form).
    """

    url_parts = None if url is None else urlparse(url)
    is_wildcard = url is not None and WILDCARD in url
    is_github_wildcard = is_wildcard and url_parts is not None and url_parts.scheme in ("https", "http")

    for option, value in [("--include-archived", include_archived), ("--include-forked", include_forked)]:
        if value and not is_github_wildcard:
            msg = f"'{option}' is only valid with a GitHub url that ends with '/{WILDCARD}'."
            raise ValueError(msg)

    if url is None or url_parts is None:
        return [None]

    if not is_wildcard:
        owner = url_parts.path.strip("/")

        # A url that names an owner on GitHub most likely omitted the wildcard; other servers may
        # host repositories at the root of the path, so their urls are passed through.
        if url_parts.hostname in _PUBLIC_GITHUB_HOSTS and owner and "/" not in owner:
            # The suggestion is built from the parsed url so that a query or fragment in the original
            # does not follow the wildcard.
            suggestion = urlunparse((url_parts.scheme, url_parts.netloc, f"/{owner}/{WILDCARD}", "", "", ""))

            msg = f"'{url}' identifies an owner rather than a repository; use '{suggestion}' to audit each of its repositories."
            raise ValueError(msg)

        return [url]

    parent_path, _, last_segment = url_parts.path.rstrip("/").rpartition("/")

    if (
        last_segment != WILDCARD
        or WILDCARD in parent_path
        or WILDCARD in url_parts.netloc
        or url_parts.params
        or url_parts.query
        or url_parts.fragment
    ):
        msg = (
            f"'{url}' is not a valid wildcard url; '{WILDCARD}' is only supported as the final path segment."
        )
        raise ValueError(msg)

    if is_github_wildcard:
        if pat is None:
            dm.WriteWarning(
                "A PAT was not provided; GitHub limits unauthenticated requests to 60 per hour and only lists public repositories.\n\n",
            )

        repositories = _EnumerateGitHubRepositories(
            url,
            url_parts,
            parent_path,
            ResolvePat(pat),
            include_archived=include_archived,
            include_forked=include_forked,
        )
    elif url_parts.scheme == "file":
        repositories = _EnumerateLocalRepositories(url, url_parts, parent_path)
    else:
        msg = f"'{url}' is not a valid wildcard url; it must begin with 'https://', 'http://', or 'file://'."
        raise ValueError(msg)

    if not repositories:
        msg = f"No repositories were found for '{url}'."
        raise ValueError(msg)

    # Copied because a list[str] is not a list[str | None]; list is invariant.
    return list(repositories)


# ----------------------------------------------------------------------
def DisableModulesWithoutUrl(
    modules: list[Module],
    arguments: dict[str, dict[str | None, dict[str, object]]],
) -> dict[str, dict[str | None, dict[str, object]]]:
    """Return a copy of the arguments in which every module that does not accept a url is disabled.

    Such a module produces the same results for every repository, so it only runs with the first.
    """

    arguments = copy.deepcopy(arguments)

    for module in modules:
        if "url" in module.GetParameters():
            continue

        module_arguments = arguments[module.name][None]

        if module.requires_explicit_include:
            module_arguments["include"] = False
        else:
            module_arguments["skip"] = True

    return arguments


# ----------------------------------------------------------------------
def InvokeForEachRepository(
    dm: DoneManager,
    modules: list[Module],
    arguments: dict[str, dict[str | None, dict[str, object]]],
    common_arguments: dict[str, object],
    urls: list[str | None],
    func: Callable[[DoneManager, dict[str, dict[str | None, dict[str, object]]], dict[str, object]], None],
) -> None:
    """Invoke func for each repository; a failure in one repository does not stop the others."""

    # Each repository receives its own copy of the arguments, as the web experience replaces them
    # with the values submitted in its window.
    for index, url in enumerate(urls):
        with dm.Nested(
            f"Auditing {'' if url is None else f"'{url}' "}({index + 1} of {len(urls)})...",
            suffix="\n",
            suppress_exceptions=True,
        ) as repository_dm:
            func(
                repository_dm,
                copy.deepcopy(arguments) if index == 0 else DisableModulesWithoutUrl(modules, arguments),
                {**common_arguments, "url": url},
            )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_PUBLIC_GITHUB_HOSTS = {"github.com", "www.github.com"}

# The maximum page size supported by the GitHub API.
_PAGE_SIZE = 100


# ----------------------------------------------------------------------
def _EnumerateGitHubRepositories(
    url: str,
    url_parts: ParseResult,
    parent_path: str,
    pat: str | None,
    *,
    include_archived: bool,
    include_forked: bool,
) -> list[str]:
    # The owner is placed in API paths, where segments such as '..' would change the resource
    # requested.
    owner = parent_path.removeprefix("/")
    if not NAME_REGEX.match(owner):
        msg = f"'{url}' is not a valid GitHub wildcard url; it must be in the form '<server>/<owner>/{WILDCARD}'."
        raise ValueError(msg)

    with GitHubApiSession(GetApiBaseUrl(url_parts.scheme, url_parts.netloc), pat) as session:
        # The repositories listed for a user are limited to public ones, even when the user is the
        # owner of the PAT, so the owner's own repositories are listed through the authenticated
        # endpoint instead.
        if _Get(session, f"/users/{owner}").json()["type"] == "Organization":
            endpoint, params = f"/orgs/{owner}/repos", {"type": "all"}
        elif pat is not None and _Get(session, "/user").json()["login"].lower() == owner.lower():
            endpoint, params = "/user/repos", {"affiliation": "owner", "visibility": "all"}
        else:
            endpoint, params = f"/users/{owner}/repos", {}

        repositories: list[dict] = []
        page = 1

        while True:
            items = _Get(session, endpoint, params={**params, "per_page": _PAGE_SIZE, "page": page}).json()

            repositories += [
                item
                for item in items
                if (include_archived or not item["archived"]) and (include_forked or not item["fork"])
            ]

            if len(items) < _PAGE_SIZE:
                break

            page += 1

    return [item["html_url"] for item in sorted(repositories, key=lambda item: item["name"].lower())]


# ----------------------------------------------------------------------
def _Get(session: GitHubApiSession, url: str, **kwargs) -> requests.Response:
    response = session.get(url, **kwargs)
    response.raise_for_status()

    return response


# ----------------------------------------------------------------------
def _EnumerateLocalRepositories(url: str, url_parts: ParseResult, parent_path: str) -> list[str]:
    if url_parts.netloc not in ("", "localhost"):
        msg = f"'{url}' is not a valid wildcard url; a 'file://' url must identify a local directory."
        raise ValueError(msg)

    directory = Path(url2pathname(parent_path or "/"))
    if not directory.is_dir():
        msg = f"'{directory}' is not a directory."
        raise ValueError(msg)

    # Hidden directories are skipped, as a wildcard is not expected to match them. Paths are resolved
    # so that a repository reachable through a symlink is audited once.
    repositories = {
        child.resolve()
        for child in directory.iterdir()
        if not child.name.startswith(".") and child.is_dir() and (child / ".git").exists()
    }

    return [repository.as_uri() for repository in sorted(repositories, key=lambda path: path.name.lower())]
