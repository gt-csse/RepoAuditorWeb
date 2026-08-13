import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.module import Module  # noqa: TC001
from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule


# ----------------------------------------------------------------------
@pluggy.HookimplMarker(APP_NAME)
def GetModule() -> Module:
    """Return the Community Standards module."""

    return CommunityStandardsModule()
