from typing import TYPE_CHECKING

import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib import plugin
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
def _GetModules() -> list[Module]:
    plugin_manager = pluggy.PluginManager(APP_NAME)

    plugin_manager.add_hookspecs(plugin)
    plugin_manager.load_setuptools_entrypoints(APP_NAME)

    modules = plugin_manager.hook.GetModule()

    # Remove the GitHub module, as it should always appear first in the list
    github_module_name = GitHubModule().name
    github_module: Module | None = None

    for index, module in enumerate(modules):
        if module.name == github_module_name:
            github_module = modules.pop(index)
            break

    assert github_module is not None

    modules.sort(key=lambda module: module.name)

    return [github_module, *modules]


# ----------------------------------------------------------------------
MODULES = _GetModules()
del _GetModules
