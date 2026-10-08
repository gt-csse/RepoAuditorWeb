import textwrap

from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.readme_heading_requirement import (
    ReadmeHeadingRequirement,
)


# ----------------------------------------------------------------------
class InstallationRequirement(ReadmeHeadingRequirement):
    """Validates that the README contains installation instructions."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Installation",
            "how to install the software",
            r"install|getting started|set ?up|requirements|dependencies",
            textwrap.dedent(
                """\
                The section should list the software's dependencies and the steps required to install it,
                ideally using a package manager that installs the dependencies automatically.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require a README heading that matches `install`,
                `getting started`, `setup`, `requirements`, or `dependencies`.

                ## Reasons for this Default

                - The JOSS review checklist asks whether there is a clearly-stated list of dependencies,
                  and reviewers verify that the software installs as documented.
                - Installation instructions are the first thing a new user needs, and missing or
                  incomplete instructions are a common reason for users to abandon software.

                ## Reasons to Override this Default

                - The installation instructions appear under a heading that does not match the default
                  pattern (`--JOSS-Installation-pattern`).
                - The installation instructions are part of documentation hosted outside of the README.
                """,
            ),
        )
