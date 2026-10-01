import textwrap

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.impl.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class ReadmeRequirement(FileExistsRequirement):
    """Validates that a README file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "README",
            "README",
            # The directories GitHub searches.
            [".", "docs", ".github"],
            textwrap.dedent(
                """\
                Add a README file to the repository. The README file should provide information about the project, including its purpose, how to install and use it, and any other relevant details. It should be written in a clear and concise manner, and it should be easy to understand for users who are new to the project.
                """
            ),
            textwrap.dedent(
                """\
                A README file is a text file that contains information about the project, such as its purpose, how to install and use it, and any other relevant details. It is typically the first file that users see when they visit a project's repository, and it serves as a guide for understanding the project and getting started with it.
                """
            ),
        )
