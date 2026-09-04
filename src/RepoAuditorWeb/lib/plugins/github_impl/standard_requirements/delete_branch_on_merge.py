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
class DeleteBranchOnMergeRequirement(Requirement):
    """Validates whether a pull request's head branch is deleted once it merges; the branch remains restorable from the pull request afterwards."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "DeleteBranchOnMerge",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the setting to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that head branches are not automatically deleted."),
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
            The default behavior is to require that head branches are automatically deleted when
            pull requests are merged.

            Note that this differs from the state of a newly created repository, where the setting is
            disabled.

            ## Reasons for this Default

            - Short-lived branches are preferable to long-lived ones. A branch that disappears when
              its work lands cannot accumulate a second change, drift behind the base branch, or
              become a place where work waits; deleting it on merge is what makes the short lifetime
              the default outcome rather than something each contributor has to remember.
            - A merged branch describes no work that is not already on the base branch, so what
              remains is a name that outlives its meaning. The branch list is a list of work in
              progress only if the entries that are no longer in progress leave it.
            - Deleting the branch by hand is a step after the merge, performed by whoever notices,
              so the branches that survive are the ones nobody attended to rather than the ones that
              were meant to. Automating it removes the judgment from a decision that has only one
              correct answer.
            - Nothing is lost. The branch is restorable from the pull request that merged it, and
              the commits are reachable from the base branch, so the ref is a convenience rather
              than the record of the work.
            - Deletion is skipped for a branch that another open pull request still references, and
              open pull requests that targeted the deleted branch are retargeted to the merged pull
              request's base branch rather than closed, so the setting does not strand work in
              review.
            - Branch protection rules and rulesets take precedence, so a branch that a rule protects
              from deletion is not deleted regardless of this setting.

            ## Reasons to Override this Default

            - Branch names carry meaning beyond the merge, such as a release or integration branch
              that is merged repeatedly and expected to persist. Rules should protect such branches,
              but a project that has not written those rules may prefer not to rely on them.
            - Something outside the repository reads the head branch after the merge, such as a
              deployment, an external tracker, or a CI job that resolves the branch name rather than
              the commit.

            Note that the setting governs head branches in this repository only; a pull request from
            a fork has its head branch in the fork, which this repository's setting does not control.
            """,
        )

        delete_branch_on_merge_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "delete_branch_on_merge",
            "branch deletion settings",
        )

        if isinstance(delete_branch_on_merge_value, EvaluateResult):
            return delete_branch_on_merge_value

        if delete_branch_on_merge_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) {action} the **Automatically delete head branches** checkbox.

                See [Managing the automatic deletion of branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{delete_branch_on_merge_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
