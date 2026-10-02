import textwrap

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.impl.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class IssueTemplateRequirement(FileExistsRequirement):
    """Validates that an ISSUE_TEMPLATE directory exists in the `.github` directory."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "IssueTemplate",
            "ISSUE_TEMPLATE",
            # GitHub no longer supports the legacy single-file template or locations outside of `.github`.
            [".github"],
            textwrap.dedent(
                """\
                Add one or more issue templates to the `.github/ISSUE_TEMPLATE` directory. Each template should prompt the reporter for the information maintainers need to act on the issue, such as steps to reproduce, expected and actual behavior, and environment details for bug reports, or the motivation and proposed solution for feature requests. GitHub only shows a template in the community profile when it defines `name` and `about` in its YAML front matter (Markdown templates) or `name` and `description` (issue forms).

                GitHub supports two kinds of issue templates:

                - [Issue templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository#creating-issue-templates), written in Markdown with YAML front matter.
                - [Issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms), written in YAML and rendered as web forms with required fields and validation.
                """
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that an ISSUE_TEMPLATE directory exists in the `.github` directory.

                ## Reasons for this Default

                - GitHub presents issue templates when a user opens a new issue, so reporters are prompted
                  for the details maintainers need before the issue is submitted.
                - Structured reports reduce the back-and-forth required to reproduce bugs or understand
                  feature requests, shortening the time to triage.
                - Separate templates for bugs, feature requests, and questions make it easier to label
                  and route issues consistently.
                - GitHub's community profile checklist includes issue templates, and their absence is
                  visible to anyone evaluating the project's health.

                ## Reasons to Override this Default

                - The organization provides default issue templates in its `.github` repository.
                  GitHub displays those templates for repositories that do not define their own, but this
                  requirement only inspects the repository itself and will not detect them.
                - Issues are disabled for the repository, or issues are tracked in an external system,
                  so templates would never be shown.
                - The repository receives few issues, such as a personal or archived repository, and the
                  overhead of maintaining templates outweighs their benefit.

                Note that this requirement only checks that the `.github/ISSUE_TEMPLATE` directory exists.
                It does not validate the templates within it, so a directory containing only a `config.yml`
                file, or templates without the front matter GitHub requires, will still be detected.
                """
            ),
            is_directory=True,
        )
