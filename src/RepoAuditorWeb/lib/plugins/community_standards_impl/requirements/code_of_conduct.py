import textwrap

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.impl.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class CodeOfConductRequirement(FileExistsRequirement):
    """Validates that a CODE_OF_CONDUCT file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "CodeOfConduct",
            "CODE_OF_CONDUCT",
            # The directories GitHub searches.
            [".", "docs", ".github"],
            textwrap.dedent(
                """\
                Add a CODE_OF_CONDUCT file to the repository. The file should define the standards of behavior expected from contributors, describe unacceptable behavior, and explain how to report violations and how they will be enforced. Adopting an established code of conduct, such as the Contributor Covenant, is a common approach.
                """
            ),
            textwrap.dedent(
                """\
                A CODE_OF_CONDUCT file establishes expectations for how participants in the project interact with one another. It signals that the project is a welcoming and inclusive environment, and it provides a documented process for addressing abusive or unwelcome behavior.
                """
            ),
        )
