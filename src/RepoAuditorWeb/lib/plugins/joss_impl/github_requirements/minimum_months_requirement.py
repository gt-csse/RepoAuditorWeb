from abc import abstractmethod
from datetime import datetime, UTC
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Markdown

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class MinimumMonthsRequirement(RationaleRequirement):
    """Requirement that validates that a date is at least a minimum number of months in the past."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        description: str,
        event: str,  # Completes the sentence "<event> on <date>", e.g. "The first commit was authored"
        resolution: Markdown,
        rationale: Markdown,
    ) -> None:
        super().__init__(name, description, rationale)

        self._event = event
        self._resolution = resolution

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "months": TyperParameter(
                int,
                6,
                OptionInfo(help="Minimum number of months."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        *,
        evaluate_all: bool,
    ) -> EvaluateResult:
        date = self._GetDate(query_data)
        months = cast(int, requirement_data["months"])

        now = datetime.now(UTC)
        elapsed_months = (now.year - date.year) * 12 + now.month - date.month - (now.day < date.day)

        context = f"{self._event} on {date.date().isoformat()}, {elapsed_months} full month(s) ago"

        if elapsed_months < months:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"{context}, but at least {months} are required.",
                self._resolution,
            )

        return self._CreateResult(module, requirement_data, EvaluateResultValue.Success, f"{context}.")

    # ----------------------------------------------------------------------
    @abstractmethod
    def _GetDate(self, query_data: dict[str, object]) -> datetime:
        """Return the date to evaluate."""
