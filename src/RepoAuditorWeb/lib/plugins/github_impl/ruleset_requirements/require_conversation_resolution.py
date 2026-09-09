import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require a pull request before
# merging" rule; conversation resolution is a parameter of that rule rather than a rule of its own.
RULE_TYPE = "pull_request"


# ----------------------------------------------------------------------
class RequireConversationResolutionRequirement(Requirement):
    """Validates whether a ruleset requires that every review comment thread on a pull request is marked as resolved before the pull request may be merged."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireConversationResolution",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the setting to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(
                    help="Require that conversation resolution is not required before merging.",
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
        rules = cast(list[dict[str, object]], query_data["response"])

        # The endpoint reports only the rules that apply, so the absence of the pull request rule
        # means the branch accepts direct pushes.
        pull_request_rule = next((rule for rule in rules if rule.get("type") == RULE_TYPE), None)

        # Review comment threads exist only on a pull request, so the setting governs nothing on a
        # branch that does not require one. Reporting a failure here would restate the absence of
        # the pull request rule, which RequirePullRequests already covers.
        if pull_request_rule is None:
            return EvaluateResult(
                EvaluateResultValue.DoesNotApply,
                "The ruleset does not require a pull request before merging, so there are no conversations to resolve.",
                None,
                None,
                self,
                module,
            )

        parameters = cast(dict[str, object], pull_request_rule.get("parameters") or {})
        resolution_value = bool(parameters.get("required_review_thread_resolution"))

        acceptable_value = not cast(bool, requirement_data["prohibit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset requires conversation resolution
            before merging.

            Note that this differs from GitHub's own default when a branch ruleset is created, where
            the setting is not selected even once the pull request rule is enabled.

            ## Reasons for this Default

            - Review comments are how a reviewer records what they want changed, and nothing else in
              the ruleset makes acting on them a condition of merging. An approval can be granted
              alongside comments that were never addressed, so without this setting the feedback
              carries no weight at merge time.
            - The gap it closes is a quiet one. A pull request with open threads looks the same at
              the merge button as one with none, so a comment is lost through inattention rather
              than through a decision to ignore it, and the loss is invisible once the branch is
              deleted.
            - Resolution is an acknowledgment rather than an agreement. A thread may be closed
              because the change was made, because the reviewer was answered, or because the
              suggestion was declined with a reason, so the setting forces the conversation to reach
              an end rather than forcing the author to comply.
            - It leaves a record of that end. Every thread on a merged pull request carries a
              deliberate close, which is what makes the review readable later by somebody asking why
              a suggestion was not taken.
            - The cost is bounded by the number of comments, and a thread that was addressed is
              closed with one click. A pull request that drew no review comments is unaffected.

            ## Reasons to Override this Default

            - The project uses review comments for remarks that are not requests, such as praise,
              questions asked out of curiosity, or notes about adjacent code, where requiring a
              close on each turns commenting into administrative work and discourages the remarks
              themselves.
            - Threads outlive the code they were attached to. A comment on a commit that a force
              push removed can become unresolvable while still blocking the merge, which leaves the
              author to reopen the pull request or seek a bypass to land work that is otherwise
              ready.
            - Resolving a thread requires write access or authorship of the pull request, so an
              outside contributor cannot close a thread that a reviewer left open, and the merge
              waits on somebody with permission rather than on the change being ready.
            - The signal degrades where the setting is enforced without agreement on what a
              resolution means. If the habit is to close threads in bulk to unblock a merge, the
              requirement records compliance rather than that the comments were read.

            Note that GitHub applies the setting to the review comment threads on the **Files
            changed** tab rather than to every comment on the pull request, so a remark left on the
            **Conversation** tab does not block the merge.

            Note also that actors granted bypass permission on the ruleset may merge with threads
            still open, so the setting describes the path that contributors take rather than one
            that cannot be circumvented.
            """,
        )

        if resolution_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            # The requirement does not apply unless the pull request rule is enabled, so the
            # checkbox is already available and the resolution does not need to enable it.
            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require conversation resolution before merging** checkbox beneath **Require a pull request before merging** in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-a-pull-request-before-merging)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{resolution_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
