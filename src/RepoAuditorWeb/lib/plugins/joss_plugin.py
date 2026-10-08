import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.module import Module  # noqa: TC001
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule


# ----------------------------------------------------------------------
@pluggy.HookimplMarker(APP_NAME)
def GetModule() -> Module:
    """Return the JOSS module."""

    return JOSSModule()
