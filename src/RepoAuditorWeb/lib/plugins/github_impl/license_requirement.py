from typing import cast, override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement


# ----------------------------------------------------------------------
class LicenseRequirement(Requirement):
    """Requirement to validate a repository's license."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "License",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                list[str],
                ["MIT License"],
                OptionInfo(help="List of acceptable licenses for the repository."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        license_value = cast(dict, query_data["response"]).get("license", {}).get("name")
        acceptable_values = cast(list[str], requirement_data["value"])

        if license_value is None:
            return EvaluateResult(EvaluateResultValue.Error, "No license value was set.", None, None, self)

        if license_value not in acceptable_values:
            acceptable_values_str = ", ".join(f"'{v}'" for v in acceptable_values)

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The license '{license_value}' is not in the list of acceptable licenses ({acceptable_values_str}).",
                None,
                None,
                self,
            )

        return EvaluateResult(
            EvaluateResultValue.Success,
            None,
            "BugBug: This is the resolution!",
            "BugBug: This is the rationale!",
            self,
        )
