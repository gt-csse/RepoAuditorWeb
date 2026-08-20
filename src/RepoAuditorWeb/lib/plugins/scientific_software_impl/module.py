from typing import override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class ScientificSoftwareModule(Module):
    """Module for validating the existence of repository files that are required for scientific software."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "ScientificSoftware",
            "Validates files that are required for scientific software.",
            [],
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "five": TyperParameter(int, 50, OptionInfo(help="Five", min=10, max=100)),
            "six": TyperParameter(bool, default=False, info=OptionInfo(help="Six")),
        }

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self, arguments: dict[str | None, dict[str, object]]
    ) -> dict[str | None, dict[str, object]]:
        return arguments
