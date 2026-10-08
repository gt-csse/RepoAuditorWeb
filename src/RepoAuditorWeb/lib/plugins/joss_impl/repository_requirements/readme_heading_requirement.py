import re

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Markdown

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.joss_impl.documents import Document


# ----------------------------------------------------------------------
class ReadmeHeadingRequirement(RationaleRequirement):
    """Requirement that validates that the README contains a heading matching a regular expression."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        topic: str,  # Completes the sentence "The README does not contain a section describing <topic>"
        default_pattern: str,
        resolution: Markdown,
        rationale: Markdown,
    ) -> None:
        super().__init__(name, f"Validates that the README contains a section describing {topic}.", rationale)

        self._topic = topic
        self._default_pattern = default_pattern
        self._resolution = resolution

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "pattern": TyperParameter(
                str,
                self._default_pattern,
                OptionInfo(help="Case-insensitive regular expression that matches the section's heading."),
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
        readme = cast("Document | None", query_data["readme"])

        if readme is None:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                "A README was not found in the root of the repository.",
                f"Add a README file to the root of the repository with a section describing {self._topic}.\n\n{self._resolution}",
            )

        pattern = cast(str, requirement_data["pattern"])
        regex = re.compile(pattern, re.IGNORECASE)

        for heading in readme.headings:
            if regex.search(heading):
                return self._CreateResult(
                    module,
                    requirement_data,
                    EvaluateResultValue.Success,
                    f"The `{heading}` heading in `{readme.path}` matches `{pattern}`.",
                )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Error,
            f"No heading in `{readme.path}` matches `{pattern}`.",
            f"Add a section to `{readme.path}` describing {self._topic}, with a heading that matches `{pattern}`.\n\n{self._resolution}",
        )
