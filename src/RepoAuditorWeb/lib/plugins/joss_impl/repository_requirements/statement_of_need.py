import textwrap

from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.readme_heading_requirement import (
    ReadmeHeadingRequirement,
)


# ----------------------------------------------------------------------
class StatementOfNeedRequirement(ReadmeHeadingRequirement):
    """Validates that the README contains a statement of need."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "StatementOfNeed",
            "the problems the software solves",
            r"statement of need|motivation|purpose|\bwhy\b",
            textwrap.dedent(
                """\
                The section should state what problems the software is designed to solve, who its target
                audience is, and how it relates to other software that addresses similar needs.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require a README heading that matches `statement of need`,
                `motivation`, `purpose`, or `why`.

                ## Reasons for this Default

                - The JOSS review checklist asks whether the authors clearly state what problems the
                  software is designed to solve and who the target audience is.
                - A statement of need allows potential users to quickly determine whether the software is
                  relevant to their work.

                ## Reasons to Override this Default

                - The statement of need appears under a heading that does not match the default pattern
                  (`--JOSS-StatementOfNeed-pattern`).
                - The statement of need is part of documentation hosted outside of the README.
                """,
            ),
        )
