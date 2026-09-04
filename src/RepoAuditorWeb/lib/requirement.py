"""Contains the Requirement object."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import auto, Enum
from typing import TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# Content authored as Markdown so that a single value renders in every experience; the console
# renders it via rich and a web page can render it natively.
type Markdown = str


# ----------------------------------------------------------------------
class EvaluateResultValue(Enum):
    """Result of evaluating a Requirement against a set of data."""

    Skipped = auto()
    DoesNotApply = auto()
    Success = auto()
    Warning = auto()
    Error = auto()


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class EvaluateResult:
    """Information associated with evaluating a Requirement against a set of data."""

    result: EvaluateResultValue
    context: Markdown | None

    resolution: Markdown | None
    rationale: Markdown | None

    requirement: Requirement
    module: Module


# ----------------------------------------------------------------------
class Requirement(ABC):
    """Abstract base class for a single requirement that can be evaluated based on data collected by a Query."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,  # Note that the description should be ~25 words or less
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
    def Evaluate(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        """Evaluate the requirement based on the results of the query."""

        if (self.requires_explicit_include and not requirement_data["include"]) or (
            not self.requires_explicit_include and requirement_data["skip"]
        ):
            return EvaluateResult(EvaluateResultValue.Skipped, None, None, None, self, module)

        return self._EvaluateImpl(module, query_data, requirement_data)

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    @abstractmethod
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        """Return a dictionary of parameters customized to the requirement itself."""

    # ----------------------------------------------------------------------
    @abstractmethod
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        """Evaluate the requirement based on the results of the query."""
