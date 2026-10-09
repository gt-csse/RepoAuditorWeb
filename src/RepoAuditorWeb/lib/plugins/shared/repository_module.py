from dataclasses import asdict
from typing import override, TYPE_CHECKING

from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.shared.repository_arguments import (
    GetRepositoryParameters,
    ResolveRepositoryArguments,
)

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
    from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class RepositoryModule(Module):
    """Module that accepts the repository's url, pat, and branch, and requires an explicit include."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,
        queries: list[Query],
    ) -> None:
        super().__init__(
            name,
            description,
            list(queries),
            requires_explicit_include=True,  # A url is required, so the module cannot run by default
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return GetRepositoryParameters()

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self, arguments: dict[str | None, dict[str, object]]
    ) -> dict[str | None, dict[str, object]]:
        arguments[None] = asdict(ResolveRepositoryArguments(arguments.get(None, {})))

        return arguments

    # ----------------------------------------------------------------------
    @override
    def CleanupModuleData(self, module_data: dict[str | None, dict[str, object]]) -> None:
        pass  # No cleanup necessary
