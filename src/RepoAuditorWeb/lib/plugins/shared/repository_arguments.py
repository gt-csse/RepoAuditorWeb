"""Parameters and argument resolution shared by modules that operate on a GitHub repository."""

import re

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class RepositoryArguments:
    """Resolved arguments used to identify and access a GitHub repository."""

    url: str
    pat: str | None
    branch: str | None


# ----------------------------------------------------------------------
def GetRepositoryParameters() -> dict[str, TyperParameter]:
    """Return the parameters used to identify and access a GitHub repository."""

    return {
        "url": TyperParameter(
            str,
            None,
            OptionInfo(help="[REQUIRED] GitHub URL (e.g. https://github.com/gt-csse/RepoAuditorWeb)."),
        ),
        "pat": TyperParameter(
            str | None,
            None,
            OptionInfo(help="GitHub Personal Access Token (PAT) or path to a local file containing the PAT."),
        ),
        "branch": TyperParameter(
            str | None,
            None,
            OptionInfo(help="Branch to evaluate. The default branch will be used if not specified."),
        ),
    }


# ----------------------------------------------------------------------
def ResolveRepositoryArguments(
    module_data: dict[str, object],
) -> RepositoryArguments:
    """Return the url, PAT, and branch, reading the PAT from a file when it names one."""

    # Get the URL
    url = module_data.get("url")

    if url is None:
        msg = "'url' is a required argument for this module."
        raise ValueError(msg)

    assert isinstance(url, str), (url, type(url))

    # The URL is passed to git, which would otherwise accept bare paths and other transports. A
    # 'file://' URL remains available so that a local repository can be audited explicitly.
    url_parts = urlparse(url)
    if not (
        (url_parts.scheme in ("https", "http") and url_parts.netloc)
        or (url_parts.scheme == "file" and url_parts.path)
    ):
        msg = (
            f"'{url}' is not a valid repository URL; it must begin with 'https://', 'http://', or 'file://'."
        )
        raise ValueError(msg)

    # Get the PAT
    pat = module_data.get("pat")
    if pat is not None:
        assert isinstance(pat, str), (pat, type(pat))

        potential_filename = Path(pat)
        if potential_filename.is_file():
            with potential_filename.open(encoding="utf-8") as f:
                pat = f.read()

            # The contents are sent to the repository's server as a credential, so a file that does
            # not hold a single token (e.g. one named by mistake) is rejected without revealing it.
            if len(pat.split()) > 1:
                msg = f"'{potential_filename}' does not contain a Personal Access Token."
                raise ValueError(msg)

        # A blank PAT would otherwise be sent as an empty credential rather than being omitted.
        pat = pat.strip()
        if not pat:
            msg = "'pat' must not be empty or contain only whitespace."
            raise ValueError(msg)

    branch = module_data.get("branch")
    assert branch is None or isinstance(branch, str), (branch, type(branch))

    # The branch is placed in API paths, where names that git rejects (such as those containing
    # '..') would change the resource requested.
    if branch is not None and (not branch or _INVALID_BRANCH_REGEX.search(branch)):
        msg = f"'{branch}' is not a valid branch name."
        raise ValueError(msg)

    return RepositoryArguments(url, pat, branch)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# A subset of the rules enforced by 'git check-ref-format'.
_INVALID_BRANCH_REGEX = re.compile(r"\.\.|@\{|//|^/|/$|^\.|/\.|\.lock(?:/|$)|[\x00-\x20\x7f~^:?*\[\\]")
