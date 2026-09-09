import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule; approval of the most recent push is a parameter of that rule rather than a rule of
# its own.
RULE_TYPE = "pull_request"


# ----------------------------------------------------------------------
class RequireApprovalOfMostRecentPushRequirement(Requirement):
    """Validates whether a ruleset requires that the most recent reviewable push to a pull request is approved by somebody other than the person who pushed it."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireApprovalOfMostRecentPush",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require approval of the most recent reviewable push."),
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

        # The endpoint reports only the rules that apply, so the absence of the pull request rule
        # means the branch accepts direct pushes.
        pull_request_rule = next((rule for rule in rules if rule.get("type") == RULE_TYPE), None)

        # The setting governs who must approve the latest commits on a pull request, so it governs
        # nothing on a branch that does not require one. Reporting a failure here would restate the
        # absence of the pull request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so there is no push to approve.",
                None,
                None,
                self,
                module,
            )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})
        last_push_value = bool(parameters.get("require_last_push_approval"))

        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset does not require approval of the most
            recent reviewable push, which matches GitHub's own default when a branch ruleset is
            created.

            ## Reasons for this Default

            - The rule presumes there is somebody other than the author available to approve. GitHub
              does not accept an approval from the person who made the most recent push, so on a
              repository maintained by one person, or by a group whose members are not consistently
              available, the pull request is blocked until somebody bypasses the ruleset.
            - It acts on every push rather than on pushes that change what would merge. A commit
              that only adjusts a comment, or a click of **Update branch** that brings in unrelated
              work, invalidates the last approval on the same terms as a substantive rewrite, so the
              cost is paid on changes where there is nothing new to review.
            - The risk it addresses is more precisely handled by **Dismiss stale pull request
              approvals when new commits are pushed**, which is driven by the diff changing rather
              than by authorship of the latest push, and which is the setting a project is more
              likely to want if it adopts only one of the two.
            - Requiring approvals already establishes that somebody other than the author agreed to
              the change, because GitHub does not count an author's approval toward the required
              count. This rule narrows that to the most recent push specifically, which is a
              stricter guarantee than many projects need.
            - Where it blocks a merge that the team considers ready, the available remedy is bypass
              permission. Routine merges performed as bypasses convert the bypass list from an
              exception path into the normal one, which weakens every other rule in the ruleset
              alongside this one.

            ## Reasons to Override this Default

            - Without the setting, the last change to a pull request can be made by its author and
              merged on the strength of approvals granted before that change existed. Enabling it
              establishes that whatever lands was seen by a second person in the state it lands in.
            - It closes the gap that a hurried author or a bad actor would use. A pull request can be
              opened small, approved, and then extended with a further commit, and the approval
              requirement ends up satisfied by code that nobody agreed to.
            - It preserves review effort in a way that dismissing stale approvals does not. Existing
              approvals are kept rather than discarded, so only the latest push needs a fresh look,
              which GitHub describes as a compromise for complex pull requests that would otherwise
              have every review dismissed.
            - The person who reviews last is positioned to check what matters most: that earlier
              feedback was applied, and that no unreviewed content was added alongside it.
            - The team is large enough that a second approver is reliably available, and somebody who
              has already reviewed the pull request may re-approve to satisfy the requirement, so the
              rule does not force a new reviewer to be found.

            Note that this setting and **Dismiss stale pull request approvals when new commits are
            pushed** address the same risk by different means and may be used together or
            separately. Dismissal discards approvals whenever a push changes the diff, while this
            setting keeps them and requires only that the most recent push carry an approval from
            somebody else.

            Note also that enabling this setting causes GitHub to reject a merge commit that is
            created manually and pushed directly to the branch, unless the contents of the merge
            exactly match the merge it would have generated for the pull request.

            Note also that actors granted bypass permission on the ruleset may merge without
            satisfying the approval requirement at all, so the setting describes the path that
            contributors take rather than one that cannot be circumvented.
            """,
        )

        if last_push_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            # The requirement does not apply unless the pull request rule is enabled, so the
            # checkbox is already available and the resolution does not need to enable it.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require approval of the most recent reviewable push** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{last_push_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
