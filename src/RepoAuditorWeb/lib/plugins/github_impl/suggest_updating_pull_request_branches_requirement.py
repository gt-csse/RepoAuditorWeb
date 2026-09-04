import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.restricted_value import GetRestrictedValue
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SuggestUpdatingPullRequestBranchesRequirement(Requirement):
    """Validates whether the update branch control is offered on every pull request whose branch is behind its base branch; the update it performs produces commits that GitHub does not sign."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SuggestUpdatingPullRequestBranches",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(
                    help="Require that updating pull request branches is always suggested.",
                ),
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
        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that updating pull request branches is not always
            suggested, which matches the state of a newly created repository. When the setting is
            disabled, the control still appears on branches that a rule requires to be up to date
            before merging; the setting only extends it to every branch that is behind.

            ## Reasons for this Default

            - The update is performed by GitHub rather than the contributor, and GitHub does not sign
              what it produces here. The merge option creates a merge commit authored by the person who
              clicked it, and the rebase option replays the branch's commits as new objects; neither
              receives the web-flow signature that GitHub applies to a merge or squash it performs on
              its own behalf. A project that requires signed commits therefore ends up with a branch it
              can no longer merge, and recovering from it requires rewriting history.
            - The rebase option is the worse of the two, because it strips the signatures from commits
              that were already signed. Every commit on the branch is replayed with a new SHA and the
              signature does not follow it, so a branch that was fully signed becomes fully unsigned.
            - The control is offered where nothing requires it, so contributors update branches that
              did not need updating. Each update rewrites or extends the branch, which restarts status
              checks and invalidates reviews on a pull request that was ready to merge.
            - Where being up to date genuinely matters, a branch protection rule or ruleset should say
              so. The rule surfaces the control on the branches it governs and blocks the merge until
              the branch is current, which is an enforced guarantee rather than a suggestion.

            ## Reasons to Override this Default

            - The project does not require signed commits, and wants contributors to be able to resolve
              a stale branch from the pull request page rather than from the command line.
            - The project relies on the merge option only and accepts unsigned merge commits, since
              that option at least preserves the signatures of the branch's existing commits.

            Note that the setting controls only where the control is offered; it does not require that
            a branch be up to date to merge, which is a branch protection rule or ruleset. Also note
            that a merge queue updates branches itself as part of forming the queue, so a repository
            using one does not need this setting to keep branches current.
            """,
        )

        allow_update_branch_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "allow_update_branch",
            "pull request branch update settings",
        )

        if isinstance(allow_update_branch_value, EvaluateResult):
            return allow_update_branch_value

        if allow_update_branch_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) {action} the **Always suggest updating pull request branches** checkbox.

                See [Managing suggestions to update pull request branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-suggestions-to-update-pull-request-branches)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{allow_update_branch_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
