import textwrap

from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class ReadmeRequirement(FileExistsRequirement):
    """Validates that a README file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Readme",
            "README",
            # The directories GitHub searches, in the order it searches them.
            [".github", ".", "docs"],
            textwrap.dedent(
                """\
                Add a README file to the repository. The README file should provide information about the project, including its purpose, how to install and use it, and any other relevant details. It should be written in a clear and concise manner, and it should be easy to understand for users who are new to the project.
                """
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a README file exists in the repository.

                ## Reasons for this Default

                - GitHub renders the README on the repository's landing page. Without one, visitors see
                  only a list of files and must infer the project's purpose from its source.
                - The README is the conventional place to document how to install, use, and contribute
                  to the project, which reduces the number of questions maintainers must answer
                  individually.
                - Package registries, such as PyPI and npm, commonly publish the README as the project's
                  long description, so its absence carries over to those listings.
                - GitHub's community profile checklist includes a README, and its absence is visible to
                  anyone evaluating the project's health.

                ## Reasons to Override this Default

                - The repository is not intended to be read by others, such as a mirror, an archive of
                  generated artifacts, or a scratch repository, so there is no audience for the file.
                - The repository's purpose is fully described elsewhere, such as in the documentation of
                  a parent project that links to it, and a README would duplicate that content.

                Note that when more than one README exists, GitHub displays the one in the `.github`
                directory first, then the repository root, and finally the `docs` directory.
                """
            ),
        )
