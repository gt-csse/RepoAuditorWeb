import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class DefaultBranchRequirement(Requirement):
    """Validates the repository's default branch, the branch that is checked out on clone and used as the base branch for new pull requests."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "DefaultBranch",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                list[str],
                ["main"],
                OptionInfo(help="List of acceptable default branch names for the repository."),
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
        default_branch_value = cast(dict, query_data["response"]).get("default_branch")
        acceptable_values = cast(list[str], requirement_data["value"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository's default branch is named `main`.

            ## Reasons for this Default

            - `main` has been the name GitHub assigns to the default branch of new repositories since
              October 2020, so it is the name contributors expect and the name that tooling defaults
              assume.
            - The default branch is the branch checked out by a clone, the base branch proposed for new
              pull requests, and the only branch copied when generating from a template or forking with
              **Copy the DEFAULT branch only**. A name that does not match convention makes each of
              these behave in a way contributors do not anticipate.

            ## Reasons to Override this Default

            - The organization standardizes on a different name (for example, `trunk` or `develop`).
            - The repository predates the convention and renaming it would break consumers, because
              GitHub Actions workflows do not follow renames and a published action referenced as
              `@<old-branch-name>` stops resolving.

            Note that renaming the default branch updates branch protection policies, the base branch of
            open pull requests, and draft releases, but collaborators must still update their local
            clones and raw file URLs are not redirected.
            """,
        )

        if default_branch_value is None or default_branch_value not in acceptable_values:
            acceptable_values_str = ", ".join(f"'{v}'" for v in acceptable_values)

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Default branch** section.
                3) Click the switch icon next to the current default branch name.
                4) Select a branch whose name is one of these values: {acceptable_values_str}.
                5) Click the **Rename branch** button.
                6) Click the **I understand, update the default branch** button.

                The repository must already contain the branch being selected, so create and push it
                first if it does not exist.

                See [Changing the default branch](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-branches-in-your-repository/changing-the-default-branch)
                for more information.
                """,
            )

            context = (
                "No default branch value was set."
                if default_branch_value is None
                else f"The default branch '{default_branch_value}' is not in the list of acceptable default branches ({acceptable_values_str})."
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                context,
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
