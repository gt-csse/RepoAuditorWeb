import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class ContributorsRequirement(RationaleRequirement):
    """Validates that commits were contributed by a minimum number of people, excluding bots."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Contributors",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require commits from at least 2 people.

                ## Reasons for this Default

                - The JOSS review checklist asks whether the project shows community engagement, such as
                  contributions from multiple developers.
                - JOSS expects multi-author projects to show evidence of issues, pull requests, and public
                  discussion, and contributions from people other than the authors are a strong signal of
                  a healthy open project.

                ## Reasons to Override this Default

                - The project has a single author. JOSS accepts single-author projects that show multiple
                  other indicators of open development, such as tagged releases or a changelog, tests and
                  continuous integration, documentation, a CONTRIBUTING file, and stated support
                  expectations (`--JOSS-Contributors-minimum 1`).
                """,
            ),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "minimum": TyperParameter(
                int,
                2,
                OptionInfo(help="Minimum number of contributors."),
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
        contributors = cast(list[str], query_data["contributors"])
        minimum = cast(int, requirement_data["minimum"])

        if len(contributors) < minimum:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"{len(contributors)} contributor(s) were found, but at least {minimum} are required.",
                textwrap.dedent(
                    """\
                    Encourage contributions from others by documenting how to contribute in a CONTRIBUTING
                    file, labeling approachable issues (for example, `good first issue`), and reviewing
                    pull requests from people outside the project.

                    Contributors are identified by the email addresses of their commits; commits authored
                    with an email address that is not associated with a GitHub account are not counted.
                    """,
                ),
            )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Success,
            f"{len(contributors)} contributor(s) were found.",
        )
