from typing import override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class CommunityStandardsModule(Module):
    """Module for validating the existence of repository files that are considered community standards."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "CommunityStandards",
            "Validates files that are considered community standards.",
            [],
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "one": TyperParameter(int, 10, OptionInfo(help="One", min=10, max=100)),
            "two": TyperParameter(str, "2", OptionInfo(help="Two")),
        }

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self, arguments: dict[str | None, dict[str, object]]
    ) -> dict[str | None, dict[str, object]]:
        return arguments
