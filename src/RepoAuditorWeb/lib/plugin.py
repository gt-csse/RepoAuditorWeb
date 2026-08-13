"""Contains the interface that Plugins must implement."""

import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.module import Module  # noqa: TC001


# ----------------------------------------------------------------------
@pluggy.HookspecMarker(APP_NAME)
def GetModule() -> Module:
    """Return a module."""

    raise NotImplementedError("hookspec")  # pragma: no cover  # noqa: EM101
