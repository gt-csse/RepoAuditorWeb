import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SupportProjectsRequirement(Requirement):
    """Validates whether the repository's projects are enabled; the setting controls the repository's Projects tab, where projects owned by the organization or user are linked."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SupportProjects",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository's projects are enabled."),
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
        has_projects_value = cast(dict, query_data["response"]).get("has_projects", False)
        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository's projects are disabled. Note that
            this does not match the state of a newly created repository, where the setting is enabled:
            projects are advanced planning functionality that a project should opt into only if it
            intends to use it.

            ## Reasons for this Default

            - Projects are advanced functionality with a real setup cost. A board becomes useful only
              once someone defines its views, fields, and workflows, so a repository that has not done
              that work gains nothing from the setting being on.
            - An enabled but unused **Projects** tab is misleading rather than neutral. It presents
              contributors with a planning surface that suggests the project's work is tracked there,
              and an empty or stale board is worse guidance than no board.
            - The tab competes with the issue tracker as the place to look for what is being worked on.
              A project that plans in its issues and milestones is better served by directing
              contributors to a single surface.
            - A board that is populated once and then abandoned misrepresents project status
              indefinitely, since items do not fall off it the way stale issues can be closed.

            ## Reasons to Override this Default

            - The project actively plans its work on a board, in which case the setting is what
              surfaces the **Projects** tab so contributors can discover the planning that governs the
              repository rather than having to know to look at the owning organization or user.
            - The project needs issues and pull requests to carry a status beyond open and closed, which
              projects provide through priority, iteration, and custom fields that the issue tracker
              alone does not offer.
            - The project relies on automations that add an item to a board when an issue or pull
              request is opened, and keeping the repository's link to that board visible makes the
              tracking that results legible to contributors.

            Note that disabling projects removes linked projects from the repository's **Projects** tab
            but does not delete them; they remain accessible at the organization or user level and the
            tab's contents return if the setting is re-enabled. Also note that this setting governs the
            repository's link to projects rather than the projects themselves, so an organization can
            still track this repository's issues on a board that the repository does not display.
            """,
        )

        if has_projects_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Features** section.
                3) {action} the **Projects** checkbox.

                See [Disabling projects in a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-projects-in-a-repository)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{has_projects_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
