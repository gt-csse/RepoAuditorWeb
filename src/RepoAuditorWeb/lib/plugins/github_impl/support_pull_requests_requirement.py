import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SupportPullRequestsRequirement(Requirement):
    """Validates whether the repository's pull requests are enabled; pull requests are how proposed changes are reviewed and are the only way a user without write access can contribute code."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SupportPullRequests",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # Pull requests are enabled by default, so the parameter names the override rather than
            # the default; a 'require' parameter defaulting to True would be a flag that is already
            # on and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository's pull requests are disabled."),
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
        has_pull_requests_value = cast(dict, query_data["response"]).get("has_pull_requests", False)
        acceptable_value = not cast(bool, requirement_data["disallow"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository's pull requests are enabled, which
            matches the state of a newly created repository.

            ## Reasons for this Default

            - Pull requests are the only way a user without write access can propose a change. With
              them disabled, the repository presents no supported route for an outside contribution,
              so a fix that someone has already written cannot be offered.
            - Pull requests are where review happens: line comments, requested changes, and approvals
              are attached to the proposal rather than to the commits that result. Disabling them
              removes the record of why a change was accepted in the form it was.
            - Branch protection and rulesets are largely enforced through pull requests, since required
              reviews, required status checks, and merge queues all gate the merge of a pull request.
              A repository that disables the feature cannot enforce those rules on the way in.
            - Pull request numbers share a namespace with issues and participate in GitHub's
              cross-referencing, so `Fixes #<number>` in a pull request body closes the issue on merge.
              Removing the feature removes the link between reported work and the change that resolved
              it.
            - The feature is the surface that a pull request template configures. A repository that
              ships `.github/pull_request_template.md` but has the feature disabled presents
              configuration that never takes effect.

            ## Reasons to Override this Default

            - The repository does not accept contributions, in which case an enabled feature invites
              proposals that no one will review. This is the case GitHub gives for turning the feature
              off.
            - The repository is a mirror or a published artifact whose source of truth is elsewhere, so
              a change made against it cannot be merged upstream and would be lost on the next
              synchronization.
            - Contributions are accepted through a different forge or a patch-based workflow such as a
              mailing list, and two intake routes would split proposals between them.

            Note that before disabling pull requests outright, restricting them is often the narrower
            fix: the **Pull requests** dropdown offers **Collaborators only**, which keeps the feature
            and its review history while limiting who can open new pull requests. Also note that
            disabling hides existing pull requests rather than erasing them; re-enabling the feature
            restores them.
            """,
        )

        if has_pull_requests_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Features** section.
                3) {action} the **Pull requests** checkbox.

                See [Disabling pull requests](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/disabling-pull-requests)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{has_pull_requests_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
