import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Block force pushes" rule.
RULE_TYPE = "non_fast_forward"


# ----------------------------------------------------------------------
class BlockForcePushesRequirement(Requirement):
    """Validates whether a ruleset blocks force pushes to the branch, so that its history can only move forward and cannot be rewritten."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "BlockForcePushes",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the rule to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that force pushes are not blocked."),
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
        rules = cast(list[dict[str, object]], query_data["response"])
        block_force_pushes_value = any(rule.get("type") == RULE_TYPE for rule in rules)

        acceptable_value = not cast(bool, requirement_data["prohibit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset blocks force pushes, which matches
            GitHub's own default when a branch ruleset is created.

            ## Reasons for this Default

            - A force push replaces the branch's history rather than adding to it. Commits that
              others have already fetched and built upon stop being reachable from the branch, so
              every collaborator holding the previous history discovers the change as a conflict
              during their next pull rather than as a reported event.
            - The rewrite is silent and leaves no record on the branch. Because the commits that
              were displaced are no longer referenced, the branch offers no evidence that anything
              was removed, and reconstructing what it previously held depends on a reflog or a local
              clone that has not yet expired.
            - A force push circumvents the review the rest of the ruleset enforces. Requiring a pull
              request, approvals, and passing status checks governs what may be added to the branch,
              but none of them examine a push that discards reviewed commits and substitutes
              unreviewed ones in their place.
            - Rewriting history invalidates work already derived from it. Open pull requests
              targeting the branch report commits that no longer exist, published commit hashes
              stop resolving, and builds or releases that recorded a hash can no longer be
              reproduced from the branch.

            ## Reasons to Override this Default

            - The ruleset targets a pattern covering branches whose history is rewritten as part of
              their normal use, such as topic branches that are rebased before merging or branches
              that tooling regenerates from another source on every run.
            - The repository is a mirror whose branches are overwritten to track an upstream that
              rewrites its own history, where a blocked force push causes the mirror to stop
              reflecting its source.

            Note that this rule blocks force pushes by users with push access rather than by
            everyone. Anyone named in the ruleset's bypass list may still force push, as may a
            repository administrator when the ruleset grants administrators bypass.
            """,
        )

        if block_force_pushes_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Block force pushes** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#block-force-pushes)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{block_force_pushes_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
