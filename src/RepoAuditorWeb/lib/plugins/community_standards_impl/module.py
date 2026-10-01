from dataclasses import asdict
from typing import override, TYPE_CHECKING

from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.community_standards_impl.community_standards_query import (
    CommunityStandardsQuery,
)
from RepoAuditorWeb.lib.plugins.github_impl.repository_arguments import (
    GetRepositoryParameters,
    ResolveRepositoryArguments,
)

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter


# ----------------------------------------------------------------------
class CommunityStandardsModule(Module):
    """Module for validating the existence of repository files that are considered community standards."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "CommunityStandards",
            "Validates files that are considered community standards.",
            [
                CommunityStandardsQuery(),
            ],
            requires_explicit_include=False,  # TODO: True
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
