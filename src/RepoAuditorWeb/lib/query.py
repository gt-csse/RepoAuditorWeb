"""Contains the Query object."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.requirement import Requirement


# ----------------------------------------------------------------------
class Query:
    """Represents a single query that collects data used to evaluate Requirements."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        requirements: list[Requirement],
    ) -> None:
        self.name = name
        self.requirements = requirements
