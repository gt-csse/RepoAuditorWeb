"""Contains the Requirement object."""

from abc import ABC, abstractmethod

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter


# ----------------------------------------------------------------------
class Requirement(ABC):
    """Abstract base class for a single requirement that can be evaluated based on data collected by a Query."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,
        *,
        requires_explicit_include: bool = False,  # If True, the requirement will not be run unless explicitly included by the user
    ) -> None:
        self.name = name
        self.description = description
        self.requires_explicit_include = requires_explicit_include

    # ----------------------------------------------------------------------
    def GetParameters(self) -> dict[str, TyperParameter]:
        """Return a dictionary of parameters that the requirement accepts."""

        base_parameters = {}

        if self.requires_explicit_include:
            base_parameters["include"] = TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help=f"Include '{self.name}' requirement in the run."),
            )
        else:
            base_parameters["skip"] = TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help=f"Skip '{self.name}' requirement in the run."),
            )

        derived_parameters = self._GetParametersImpl()

        for param_name in derived_parameters:
            if param_name in base_parameters:
                msg = f"Parameter '{param_name}' is reserved by Requirement and may not be used."
                raise ValueError(msg)

        return {**base_parameters, **derived_parameters}

    # ----------------------------------------------------------------------
    @abstractmethod
    def Evaluate(self, query_results: dict) -> bool:
        """Evaluate the requirement based on the results of the query."""

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    @abstractmethod
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        """Return a dictionary of parameters customized to the requirement itself."""
