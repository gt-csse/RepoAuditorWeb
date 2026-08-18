"""Contains the Module object."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.query import Query
    from RepoAuditorWeb.lib.requirement import Requirement


# ----------------------------------------------------------------------
class Module(ABC):
    """Abstract base class for a collection of Queries that operate on a consistent set of data."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,
        queries: list[Query],
        *,
        requires_explicit_include: bool = False,  # If True, the module will not be run unless explicitly included by the user
    ) -> None:
        # Ensure that requirement names are unique across all queries
        requirement_names: dict[str, Requirement] = {}

        for query in queries:
            for requirement in query.requirements:
                prev_requirement = requirement_names.get(requirement.name)
                if prev_requirement is not None:
                    msg = f"The requirement name '{requirement.name}' is used in both '{prev_requirement.__class__.__name__}' and '{requirement.__class__.__name__}'. Requirement names must be unique across all queries in a module."
                    raise ValueError(msg)

                requirement_names[requirement.name] = requirement

        self.name = name
        self.description = description
        self.queries = queries
        self.requires_explicit_include = requires_explicit_include

    # ----------------------------------------------------------------------
    def GetParameters(self) -> dict[str, TyperParameter]:
        """Return a dictionary of parameters that the module accepts."""

        base_parameters = {}

        if self.requires_explicit_include:
            base_parameters["include"] = TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help=f"Include '{self.name}' module in the run."),
            )
        else:
            base_parameters["skip"] = TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help=f"Skip '{self.name}' module in the run."),
            )

        derived_parameters = self._GetParametersImpl()

        for param_name in derived_parameters:
            if param_name in base_parameters:
                msg = f"Parameter '{param_name}' is reserved by Module and may not be used."
                raise ValueError(msg)

        return {**base_parameters, **derived_parameters}

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    @abstractmethod
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        """Return a dictionary of parameters customized to the module itself."""
