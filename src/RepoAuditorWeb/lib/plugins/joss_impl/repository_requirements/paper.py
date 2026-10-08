import textwrap

from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper


# ----------------------------------------------------------------------
class PaperRequirement(RationaleRequirement):
    """Validates that a JOSS paper (`paper.md`) exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Paper",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require that a `paper.md` file exists in the repository.

                ## Reasons for this Default

                - JOSS requires that the paper (`paper.md`, its BibTeX file, and any figures) is hosted
                  in the same repository as the software.

                ## Reasons to Override this Default

                - The paper is on a branch other than the one being audited; JOSS permits the paper to be
                  on a short-lived branch created from the default branch (`--branch <name>`).
                - The software is not being prepared for submission to JOSS.
                """,
            ),
        )

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
        paper = cast("Paper | None", query_data["paper"])

        if paper is None:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                "`paper.md` was not found in the repository.",
                textwrap.dedent(
                    """\
                    Add a `paper.md` file and a `paper.bib` file to the repository (commonly in a `paper`
                    directory), following the [JOSS paper format](https://joss.readthedocs.io/en/latest/paper.html)
                    and the [example paper](https://joss.readthedocs.io/en/latest/example_paper.html).

                    Use the [Open Journals GitHub Action](https://github.com/marketplace/actions/open-journals-pdf-generator)
                    to verify that the paper compiles.
                    """,
                ),
            )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Success,
            f"The paper was found at `{paper.path}`.",
        )
