import textwrap

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.impl.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class PullRequestTemplateRequirement(FileExistsRequirement):
    """Validates that a PULL_REQUEST_TEMPLATE file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PullRequestTemplate",
            "PULL_REQUEST_TEMPLATE",
            # The directories GitHub searches.
            [".github", ".", "docs"],
            textwrap.dedent(
                """\
                Add a `pull_request_template.md` file to the `.github` directory, the root of the repository, or the `docs` directory. GitHub automatically populates the body of every new pull request with the template's contents, so it should prompt the author for the information reviewers need, such as a summary of the change, related issues, testing performed, and a checklist of project conventions.

                See [Creating a pull request template for your repository](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository) for more information.
                """
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a PULL_REQUEST_TEMPLATE file exists in the repository.

                ## Reasons for this Default

                - GitHub populates new pull requests with the template, so authors are prompted for the
                  details reviewers need before the pull request is submitted.
                - Consistent pull request descriptions make changes easier to review, and make the
                  project's history easier to understand after the pull request is merged.
                - A checklist within the template reminds authors of project conventions, such as adding
                  tests or updating documentation, reducing the number of review iterations.
                - GitHub's community profile checklist includes a pull request template, and its absence
                  is visible to anyone evaluating the project's health.

                ## Reasons to Override this Default

                - The organization provides a default pull request template in its `.github` repository.
                  GitHub uses that template for repositories that do not define their own, but this
                  requirement only inspects the repository itself and will not detect it.
                - The repository does not accept pull requests, such as a personal, mirrored, or archived
                  repository, so the template would never be shown.
                - Pull request templates are stored in a `PULL_REQUEST_TEMPLATE` directory. GitHub only
                  applies those templates when they are selected via a query parameter, and this
                  requirement will not detect them.
                """
            ),
        )
