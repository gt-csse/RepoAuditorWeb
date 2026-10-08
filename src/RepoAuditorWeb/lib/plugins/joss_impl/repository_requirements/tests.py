import textwrap

from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import FileExistsRequirement


# ----------------------------------------------------------------------
# The class is not named `TestsRequirement` because pytest would collect it as a test class.
class AutomatedTestsRequirement(FileExistsRequirement):
    """Validates that a tests directory exists in the root of the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Tests",
            ["test", "tests", "testing", "spec"],
            ["."],
            textwrap.dedent(
                """\
                Add automated tests to a `tests` directory in the root of the repository, and run them in
                continuous integration (for example, with
                [GitHub Actions](https://docs.github.com/en/actions/use-cases-and-examples/building-and-testing)).
                Document how to run the tests in the README or the CONTRIBUTING file.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a test, tests, testing, or spec directory exists in
                the root of the repository.

                ## Reasons for this Default

                - The JOSS review checklist asks whether there are automated tests, or manual steps
                  described, so that the functionality of the software can be verified.
                - Automated tests allow reviewers and contributors to verify that the software works as
                  claimed, and that changes do not break existing functionality.

                ## Reasons to Override this Default

                - The tests are stored elsewhere, such as alongside the source code
                  (for example, `src/<package>/tests`) or in files named `test_*.py`.
                - The software is verified through documented manual steps rather than automated tests.
                """,
            ),
            is_directory=True,
        )
