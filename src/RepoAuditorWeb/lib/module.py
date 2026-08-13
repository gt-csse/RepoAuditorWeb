"""Contains the Module object."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.typer_parameter import TyperParameter


# ----------------------------------------------------------------------
class Module(ABC):
    """Abstract base class for a collection of Queries that operate on a consistent set of data."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,
        *,
        requires_explicit_include: bool = False,  # If True, the module will not be run unless explicitly included by the user
    ) -> None:
        assert "_" not in name, "Module names cannot contain underscores"

        self.name = name
        self.description = description
        self.requires_explicit_include = requires_explicit_include

    # ----------------------------------------------------------------------
    @abstractmethod
    def GetParameters(self) -> dict[str, TyperParameter]:
        """Return a dictionary of parameters that the module accepts."""
