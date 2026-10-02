"""Parameters and argument resolution shared by modules that operate on a GitHub repository."""

from dataclasses import dataclass
from pathlib import Path

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

    # Get the PAT
    pat = module_data.get("pat")
    if pat is not None:
        assert isinstance(pat, str), (pat, type(pat))

        potential_filename = Path(pat)
        if potential_filename.is_file():
            with potential_filename.open(encoding="utf-8") as f:
                pat = f.read()

        # A blank PAT would otherwise be sent as an empty credential rather than being omitted.
        pat = pat.strip()
        if not pat:
            msg = "'pat' must not be empty or contain only whitespace."
            raise ValueError(msg)

    branch = module_data.get("branch")
    assert branch is None or isinstance(branch, str), (branch, type(branch))

    return RepositoryArguments(url, pat, branch)
