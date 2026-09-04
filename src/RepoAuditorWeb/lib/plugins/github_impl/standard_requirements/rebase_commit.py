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
class RebaseCommitRequirement(Requirement):
    """Validates whether pull requests can be merged by rebasing; the method replays commits onto the base branch as new commits, dropping their signatures."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RebaseCommit",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that rebase merging is enabled."),
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
            The default behavior is to require that rebase merging is disallowed.

            Note that this differs from the state of a newly created repository, which allows all
            three merge methods.

            ## Reasons for this Default

            - Rebasing replays each of the branch's commits onto the base branch as a new commit with
              updated committer information and a new SHA, so any signature the original carried does
              not follow it. The result is a history of unsigned commits.
            - GitHub cannot sign the replacements either. It does not hold the committer's signing key
              and the commits are not its own to attest to, so unlike a merge commit or a squash
              commit there is no web-flow signature to substitute. Requiring signed commits on the
              base branch therefore blocks the method outright, with GitHub reporting that rebase
              merges cannot be automatically signed.
            - This makes the method the worst of the three for attribution. A merge commit preserves
              the branch's signed commits as authored, and a squash commit at least lands one signed
              object; rebasing lands several commits, none of which is signed by anyone.
            - The commits that land are not the commits that were tested, since each is a new object
              with a different parent from the one status checks ran against, and the branch's
              intermediate states are replayed onto a base that has moved since.
            - The method also drops commits that were empty to begin with, so the history that lands
              is not the history that was reviewed.

            ## Reasons to Override this Default

            - A branch protection rule or ruleset requires a linear commit history and the project
              wants the branch's individual commits on the base branch rather than one squashed
              commit, which is what distinguishes this method from squash merging.
            - The project curates its branches so that each commit is a meaningful, independently
              reviewable step, and treats losing those boundaries to a squash as the greater cost.
            - The project does not rely on commit signatures for attribution, having established
              authorship through review records or the pull request itself instead.

            Note that a repository must keep at least one merge method enabled, so disallowing this one
            requires that merge commits or squash merging remain available. Also note that merge queues
            do not honor these settings, since the queue controls the method used for the merges it
            performs, and that restricting a single branch to a particular method is done with a
            ruleset's allowed merge methods rather than here. GitHub refuses to rebase when it cannot
            do so safely, in which case the work of replaying the commits falls to the branch's author.
            """,
        )

        allow_rebase_merge_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "allow_rebase_merge",
            "rebase merge settings",
        )

        if isinstance(allow_rebase_merge_value, EvaluateResult):
            return allow_rebase_merge_value

        if allow_rebase_merge_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) {action} the **Allow rebase merging** checkbox.

                See [Configuring commit rebasing for pull requests](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-rebasing-for-pull-requests)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{allow_rebase_merge_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
