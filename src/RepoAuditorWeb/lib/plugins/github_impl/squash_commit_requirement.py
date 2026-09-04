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
class SquashCommitRequirement(Requirement):
    """Validates whether pull requests can be merged by squashing; the method rewrites the branch's commits into one, dropping their authorship and signatures."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SquashCommit",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that squash merging is enabled."),
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
            The default behavior is to require that squash merging is disallowed.

            Note that this differs from the state of a newly created repository, which allows all
            three merge methods.

            ## Reasons for this Default

            - Squashing rewrites the branch's commits into a new commit that no contributor created
              locally, so any signature they carried cannot follow them onto the base branch. The
              replacement is signed with GitHub's web-flow key, which attests that GitHub performed
              the merge rather than that a developer wrote the change.
            - A merge commit is signed with the same web-flow key, but it leaves the branch's signed
              commits reachable as they were authored. Squashing discards them, so the history retains
              no commit signed by the person who wrote the code and the web-flow signature is the only
              one left to verify.
            - Verification of a squashed commit therefore establishes less than it appears to. A reader
              checking signatures finds a valid one on every commit while none of them attests to the
              identity of an author, which is weaker than an unsigned history that does not invite the
              inference.
            - Squashing collapses an entire branch into one revision, so `git bisect` identifies the
              branch rather than the change within it, and `git blame` attributes every line the branch
              touched to a single commit.
            - The commit that lands on the base branch is not the commit that was tested on the branch,
              since it is a new object with a different tree lineage and no parent among the commits
              that status checks ran against.

            ## Reasons to Override this Default

            - The project treats a pull request as one logical change and wants one commit per change
              on the base branch, which is the purpose of the method; this matters most when branches
              accumulate fixup and work-in-progress commits that carry no meaning after review.
            - A branch protection rule or ruleset requires a linear commit history, which merge commits
              cannot satisfy. Squashing produces a linear history without asking contributors to replay
              commits themselves, which rebasing does when GitHub cannot resolve a conflict.
            - The project does not rely on commit signatures for attribution, having established
              authorship through review records or the pull request itself instead.

            Note that a repository must keep at least one merge method enabled, so disallowing this one
            requires that merge commits or rebase merging remain available. Also note that merge queues
            do not honor these settings, since the queue controls the method used for the merges it
            performs, and that restricting a single branch to a particular method is done with a
            ruleset's allowed merge methods rather than here.
            """,
        )

        allow_squash_merge_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "allow_squash_merge",
            "squash merge settings",
        )

        if isinstance(allow_squash_merge_value, EvaluateResult):
            return allow_squash_merge_value

        if allow_squash_merge_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) {action} the **Allow squash merging** checkbox.

                See [Configuring commit squashing for pull requests](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{allow_squash_merge_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
