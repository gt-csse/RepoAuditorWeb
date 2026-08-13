import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.module import Module  # noqa: TC001
from RepoAuditorWeb.lib.plugins.scientific_software_impl.module import ScientificSoftwareModule


# ----------------------------------------------------------------------
@pluggy.HookimplMarker(APP_NAME)
def GetModule() -> Module:
    """Return the Scientific Software module."""

    return ScientificSoftwareModule()
