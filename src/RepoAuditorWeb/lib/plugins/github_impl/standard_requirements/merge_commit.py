import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.restricted_value import GetRestrictedValue
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class MergeCommitRequirement(Requirement):
    """Validates whether pull requests can be merged with a merge commit; the method merges with `--no-ff`, preserving the branch's individual commits."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "MergeCommit",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # Merge commits are enabled by default, so the parameter names the override rather than
            # the default; a 'require' parameter defaulting to True would be a flag that is already
            # on and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that merge commits are disallowed."),
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
        acceptable_value = not cast(bool, requirement_data["disallow"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that merge commits are allowed, which matches the state
            of a newly created repository.

            ## Reasons for this Default

            - The merge commit is the only merge method that leaves the branch's commits reachable as
              they were authored. Squashing and rebasing both rewrite them, so the commit that was
              tested on the branch is not the commit that lands on the base branch.
            - The method records the integration itself. A merge commit has both the base branch and
              the merged branch as parents, so `git log --first-parent` reads as a list of integrations
              while the full history retains the work that each one brought in.
            - Preserving the authored commits keeps `git bisect` and `git blame` pointed at the change
              that actually introduced a behavior, rather than at a squashed commit that collapses an
              entire branch into one revision.
            - The method requires nothing of the contributor. Rebasing is refused when it would produce
              a conflict that GitHub cannot resolve, which pushes the work of replaying commits back
              onto the branch's author; a merge commit can represent that resolution instead.
            - Disabling every merge method leaves pull requests with no merge button at all, so the
              repository has to keep at least one enabled and this is the method that discards the
              least information.

            ## Reasons to Override this Default

            - A branch protection rule or ruleset requires a linear commit history, which merge commits
              cannot satisfy. Such a repository must allow squash merging, rebase merging, or both, and
              leaving this method enabled offers contributors a merge button that the rule will reject.
            - The project treats a pull request as a single logical change and wants one commit per
              change on the base branch, in which case squash merging produces the intended history and
              this method would let a branch's intermediate commits through.
            - The project regards merge commits as noise in the history it publishes, since `--no-ff`
              means one is created even where the branch could have fast-forwarded.
            - Enabling exactly one merge method is how a repository enforces that method, so a project
              that has standardized on squashing or rebasing disables this one to remove the choice.

            Note that merge queues do not honor these settings, since the queue controls the method
            used for the merges it performs. Also note that this setting governs the whole repository,
            so restricting a single branch to a particular method is done with a ruleset's allowed
            merge methods rather than here; a ruleset can only narrow what the repository allows, so
            this setting has to remain enabled for a ruleset to permit it anywhere.
            """,
        )

        allow_merge_commit_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "allow_merge_commit",
            "merge settings",
        )

        if isinstance(allow_merge_commit_value, EvaluateResult):
            return allow_merge_commit_value

        if allow_merge_commit_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) {action} the **Allow merge commits** checkbox.

                See [Configuring commit merging for pull requests](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{allow_merge_commit_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
