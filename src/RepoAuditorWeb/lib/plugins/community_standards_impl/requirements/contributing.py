import textwrap

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.impl.file_exists_requirement import (
    FileExistsRequirement,
)


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
                Add a CONTRIBUTING file to the repository. The file should explain how to report issues, propose changes, set up a development environment, run tests, and submit pull requests, along with any coding conventions or review expectations the project enforces.

                GitHub references these CONTRIBUTING files as examples:

                - [GitHub Docs](https://github.com/github/docs/blob/main/CONTRIBUTING.md)
                - [Ruby on Rails](https://github.com/rails/rails/blob/main/CONTRIBUTING.md)
                - [Open Government](https://github.com/opengovernment/opengovernment/blob/master/CONTRIBUTING.md)
                """
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a CONTRIBUTING file exists in the repository.

                ## Reasons for this Default

                - GitHub links to the CONTRIBUTING file when contributors open an issue or pull request,
                  so guidelines are presented at the moment they are most relevant.
                - Documenting the contribution process up front reduces the number of submissions that
                  must be returned for missing tests, incorrect formatting, or an unexpected workflow.
                - The file lowers the barrier for first-time contributors, who otherwise must infer the
                  project's expectations from its history or ask a maintainer directly.
                - GitHub's community profile checklist includes a CONTRIBUTING file, and its absence is
                  visible to anyone evaluating the project's health.

                ## Reasons to Override this Default

                - The organization provides a default CONTRIBUTING file in its `.github` repository.
                  GitHub displays that file for repositories that do not define their own, but this
                  requirement only inspects the repository itself and will not detect it.
                - The repository does not accept outside contributions, such as a personal, mirrored, or
                  archived repository, so there is no process to document.
                - Contribution guidelines are maintained elsewhere, such as in a parent project's
                  documentation, and a CONTRIBUTING file would duplicate that content.

                Note that a CONTRIBUTING file should be kept in sync with the project's tooling; outdated
                setup or testing instructions can be more confusing to contributors than none at all.
                """
            ),
        )
