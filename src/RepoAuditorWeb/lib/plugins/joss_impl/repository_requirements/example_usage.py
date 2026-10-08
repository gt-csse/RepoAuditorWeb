import textwrap

from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.readme_heading_requirement import (
    ReadmeHeadingRequirement,
)


# ----------------------------------------------------------------------
class ExampleUsageRequirement(ReadmeHeadingRequirement):
    """Validates that the README contains examples of how to use the software."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "ExampleUsage",
            "how to use the software",
            r"usage|example|tutorial|quick ?start|getting started|how to use",
            textwrap.dedent(
                """\
                The section should include examples that demonstrate how to use the software to solve
                real-world problems, ideally ones that readers can run and whose output they can compare.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require a README heading that matches `usage`, `example`,
                `tutorial`, `quickstart`, `getting started`, or `how to use`.

                ## Reasons for this Default

                - The JOSS review checklist asks whether the authors include examples of how to use the
                  software, ideally to solve real-world analysis problems.
                - Examples are often the fastest way for a new user to learn the software, and reviewers
                  use them to confirm the software's functional claims.

                ## Reasons to Override this Default

                - The examples appear under a heading that does not match the default pattern
                  (`--JOSS-ExampleUsage-pattern`).
                - The examples are part of documentation hosted outside of the README, such as tutorials
                  or notebooks.
                """,
            ),
        )
