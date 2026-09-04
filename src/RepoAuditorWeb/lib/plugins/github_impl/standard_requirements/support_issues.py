import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SupportIssuesRequirement(Requirement):
    """Validates whether the repository's issue tracker is enabled; issues are where bug reports, tasks, and feature requests are filed and referenced."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SupportIssues",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The tracker is enabled by default, so the parameter names the override rather than the
            # default; a 'require' parameter defaulting to True would be a flag that is already on
            # and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository's issue tracker is disabled."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        has_issues_value = cast(dict, query_data["response"]).get("has_issues", False)
        acceptable_value = not cast(bool, requirement_data["disallow"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository's issue tracker is enabled, which
            matches the state of a newly created repository.

            ## Reasons for this Default

            - Issues are the only place a user without write access can report a defect. With the
              tracker disabled, the repository presents no supported way to report one, so reports
              arrive as unsolicited pull requests, email, or nothing at all.
            - Issue numbers share a namespace with pull requests and are the target of GitHub's
              cross-referencing: `#<number>` in a commit message or comment links to the issue, and a
              pull request body containing `Fixes #<number>` closes it on merge. Disabling the tracker
              removes the record that this linking is built around.
            - Issues are what populate the repository's history of known defects, so a search for a
              symptom finds the previous report and its resolution. Discussion held elsewhere is not
              searchable from the repository.
            - The tracker is the surface that issue templates and forms configure. A repository that
              ships `.github/ISSUE_TEMPLATE` content but has the feature disabled presents contributors
              with configuration that never takes effect.

            ## Reasons to Override this Default

            - The repository does not accept contributions or bug reports, in which case an enabled
              tracker invites reports that no one will triage. This is the case GitHub gives for
              turning the feature off.
            - Tracking happens somewhere else (an external tracker, or a separate issues-only
              repository used because GitHub does not provide issues-only access permissions), and two
              trackers would split reports between them.
            - The repository is a mirror or a published artifact whose source of truth is elsewhere, so
              reports filed against it cannot be acted upon.

            Note that before disabling the tracker outright, restricting it is often the narrower fix:
            the **Issues** dropdown offers **Collaborators only**, which keeps the tracker and its
            history while limiting who can open new issues. Also note that disabling hides existing
            issues rather than erasing them; re-enabling the feature restores them.
            """,
        )

        if has_issues_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Features** section.
                3) {action} the **Issues** checkbox.

                See [Disabling issues](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-issues)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{has_issues_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
