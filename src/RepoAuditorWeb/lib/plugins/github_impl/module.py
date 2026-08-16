from typing import override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.parameters import TyperParameter


# ----------------------------------------------------------------------
class GitHubModule(Module):
    """Module for validating GitHub repository configuration settings."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "GitHub",
            "Validates GitHub configuration settings.",
            [],
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "three": TyperParameter(int, 30, OptionInfo(help="Three", min=10, max=100)),
            "four": TyperParameter(str, "4", OptionInfo(help="Four")),
        }
