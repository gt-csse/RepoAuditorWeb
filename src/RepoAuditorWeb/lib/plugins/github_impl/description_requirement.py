from enum import StrEnum
from typing import cast, override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement


# ----------------------------------------------------------------------
class Values(StrEnum):
    """Enumeration of possible values for the DescriptionRequirement."""

    Populated = "populated"
    AllowEmpty = "allow_empty"
    Empty = "empty"


# ----------------------------------------------------------------------
class DescriptionRequirement(Requirement):
    """Requirement to validate a repository's description."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Description",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                Values,
                Values.Populated,
                OptionInfo(help="How to verify the repository description."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        response = cast(dict, query_data["response"])
        value = requirement_data["value"]

        if value == Values.Populated:
            if response.get("description"):
                result = EvaluateResultValue.Success
                context = None
            else:
                result = EvaluateResultValue.Error
                context = "The repository description is empty."
        elif value == Values.AllowEmpty:
            result = EvaluateResultValue.Success
            context = None
        elif value == Values.Empty:
            if response.get("description"):
                result = EvaluateResultValue.Error
                context = "The repository description is populated."
            else:
                result = EvaluateResultValue.Success
                context = None
        else:
            assert False, value  # noqa: B011, PT015  # pragma: no cover

        return EvaluateResult(result, context, None, None, self)
