import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class TemplateRequirement(Requirement):
    """Validates whether the repository is a template, which generates new repositories with unrelated histories rather than forks."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Template",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository is a template repository."),
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
        is_template_value = cast(dict, query_data["response"]).get("is_template", False)
        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository is not a template repository, which
            controls whether GitHub offers a **Use this template** button to generate new repositories
            from its contents.

            ## Reasons for this Default

            - Repositories generated from a template have unrelated histories, so changes cannot flow
              back to the template through a pull request. Offering the button on a repository that is
              not intended to be a starting point invites copies that can never contribute fixes
              upstream.
            - Generating from a template copies only the default branch unless the other branches are
              explicitly requested, so a repository whose value spans multiple branches is a poor
              template.

            ## Reasons to Override this Default

            - The repository exists to be the starting point for new repositories, in which case
              generating is preferable to forking because the result has no fork relationship and no
              inherited history.

            Note that a template repository cannot include files stored using Git LFS.
            """,
        )

        if is_template_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Template repository** checkbox.
                3) {action} the **Template repository** checkbox.

                See [Creating a template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{is_template_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
