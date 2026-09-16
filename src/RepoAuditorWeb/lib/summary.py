"""Contains the Summary object."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from RepoAuditorWeb.lib.requirement import EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.requirement import EvaluateResult


# The names are shared by every experience that reports results so that a result value is identified
# consistently regardless of how it is presented.
RESULT_VALUE_NAMES = {
    EvaluateResultValue.Skipped: "skipped",
    EvaluateResultValue.DoesNotApply: "does_not_apply",
    EvaluateResultValue.Success: "success",
    EvaluateResultValue.Warning: "warning",
    EvaluateResultValue.Error: "error",
}


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Summary:
    """Counts of each result value produced by a run."""

    skipped: int = 0
    does_not_apply: int = 0
    success: int = 0
    warning: int = 0
    error: int = 0

    # ----------------------------------------------------------------------
    @classmethod
    def Create(cls, results: list[EvaluateResult]) -> Summary:
        """Tally the results by their result value."""

        counts = dict.fromkeys(RESULT_VALUE_NAMES.values(), 0)

        for result in results:
            counts[RESULT_VALUE_NAMES[result.result]] += 1

        return cls(**counts)

    # ----------------------------------------------------------------------
    @property
    def total(self) -> int:
        """The number of results tallied."""

        return self.skipped + self.does_not_apply + self.success + self.warning + self.error

    # ----------------------------------------------------------------------
    def CalcPercentage(self, count: int) -> str:
        """Format count as a percentage of the total."""

        if self.total == 0:
            return "0.00%"

        return f"{(count / self.total) * 100:.2f}%"
