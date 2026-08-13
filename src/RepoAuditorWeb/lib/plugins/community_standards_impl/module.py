from typing import override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.typer_parameter import TyperParameter


# ----------------------------------------------------------------------
class CommunityStandardsModule(Module):
    """Module for validating the existence of repository files that are considered community standards."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "CommunityStandards",
            "Validates files that are considered community standards.",
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def GetParameters(self) -> dict[str, TyperParameter]:
        return {
            "one": TyperParameter(int, 10, OptionInfo(help="One", min=10, max=100)),
            "two": TyperParameter(str, "2", OptionInfo(help="Two")),
        }
