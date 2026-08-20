"""Contains the Query object."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.requirement import Requirement


# ----------------------------------------------------------------------
class Query(ABC):
    """Represents a single query that collects data used to evaluate Requirements."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        requirements: list[Requirement],
    ) -> None:
        self.name = name
        self.requirements = requirements

    # ----------------------------------------------------------------------
    @abstractmethod
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        """Return a dictionary of data that will be used to evaluate the requirements for this query.

        Derived classes may return the provided module data unmodified, add values, or return a completely different
        dictionary of data. The query will be skipped if None is returned.
        """
