import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.module import Module  # noqa: TC001
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule


# ----------------------------------------------------------------------
@pluggy.HookimplMarker(APP_NAME)
def GetModule() -> Module:
    """Return the GitHub module."""

    return GitHubModule()
