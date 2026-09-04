import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SupportDiscussionsRequirement(Requirement):
    """Validates whether the repository's discussions are enabled; discussions are a forum for questions and open-ended conversation that is separate from the issue tracker."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SupportDiscussions",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository's discussions are enabled."),
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
        has_discussions_value = cast(dict, query_data["response"]).get("has_discussions", False)
        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository's discussions are disabled, which
            matches the state of a newly created repository.

            ## Reasons for this Default

            - Discussions are a second inbound channel that overlaps the issue tracker, so a project
              running both must triage two queues and decide for each incoming report which one it
              belongs in. A project that has not committed to that moderation effort is better served
              by the single queue it already has.
            - Discussions have no state to close and no cross-referencing role: they are not the target
              of `Fixes #<number>`, they do not appear in a milestone, and they cannot be added to a
              project board the way an issue can. Work that needs to be tracked has to be re-filed as
              an issue anyway.
            - Discussions are a search surface distinct from issues, so a contributor searching for a
              previously answered question finds it only if they search the surface it was answered on.
              Splitting a project's history across both makes prior answers harder to find.
            - Enabling the feature without seeding categories or answering anything presents
              contributors with an empty forum, which reads as an unmaintained support channel rather
              than an invitation.
            - The feature is unnecessary for a repository whose audience is its own maintainers, since
              the conversation it hosts is already happening in pull request review.

            ## Reasons to Override this Default

            - The project receives support questions that are not defects, which is the case GitHub
              gives for the feature. Routing them to discussions keeps the issue tracker limited to
              actionable work, and a question-and-answer category lets the accepted response be marked
              as the answer so later readers find it.
            - The project wants to gather community input on direction before committing to work, which
              discussions support through polls, announcements, and upvoting in a format that does not
              require every thread to resolve.
            - Discussions replace a chat service or mailing list that the project would otherwise depend
              on, keeping the conversation on the same host as the code and visible to anyone with
              repository access.

            Note that enabling discussions does not by itself route questions away from the issue
            tracker; a `contact_links` entry in `.github/ISSUE_TEMPLATE/config.yml` is what presents
            discussions as the destination when a contributor starts to open an issue. Also note that
            an organization's discussions are hosted by a source repository, so this setting may be
            enabled on a repository to serve the organization rather than the repository itself.
            """,
        )

        if has_discussions_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Features** section.
                3) {action} the **Discussions** checkbox.

                See [Enabling or disabling GitHub Discussions for a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/enabling-or-disabling-github-discussions-for-a-repository)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{has_discussions_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
