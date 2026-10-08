import textwrap

from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import FileExistsRequirement


# ----------------------------------------------------------------------
class ContributingRequirement(FileExistsRequirement):
    """Validates that a CONTRIBUTING file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Contributing",
            "CONTRIBUTING",
            # The directories GitHub searches, in the order it searches them.
            [".github", ".", "docs"],
            textwrap.dedent(
                """\
                Add a CONTRIBUTING file to the repository that explains how third parties can contribute
                to the software, report issues or problems with the software, and seek support.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a CONTRIBUTING file exists in the repository.

                ## Reasons for this Default

                - The JOSS review checklist asks whether there are clear guidelines for third parties
                  wishing to contribute to the software, report issues or problems with the software,
                  and seek support.

                ## Reasons to Override this Default

                - The community guidelines are documented in the README or in documentation hosted
                  outside of the repository.
                """,
            ),
        )
