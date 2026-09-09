import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# The rule type reported by the branch rules endpoint for GitHub's "Require signed commits" rule.
RULE_TYPE = "required_signatures"


# ----------------------------------------------------------------------
class RequireSignedCommitsRequirement(Requirement):
    """Validates whether a ruleset requires that commits pushed to branches matching its pattern carry a signature that GitHub has verified against a known identity."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "RequireSignedCommits",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the rule to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that signed commits are not required."),
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
        signed_commits_value = any(rule.get("type") == RULE_TYPE for rule in rules)

        acceptable_value = not cast(bool, requirement_data["disallow"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that a ruleset requires signed commits.

            Note that this differs from GitHub's own default when a branch ruleset is created, where
            the rule is not selected.

            ## Reasons for this Default

            - The author and committer recorded in a commit are strings the committing tool writes
              at the author's discretion. Nothing in Git checks them, so any contributor can produce
              a commit attributed to anyone else, and the history displays that attribution as
              though it were established. A signature is the only part of a commit that ties it to a
              key rather than to a claim.
            - Attribution on the mainline branch is what the rest of the repository's process is
              recorded against. A review, an approval, and a status check all refer to commits, so
              an unverifiable author undermines the record those controls produce rather than merely
              being cosmetic.
            - The rule is enforced at the point of the push, so the branch cannot accumulate
              unverifiable commits that would have to be rewritten later. Enabling it on a
              repository whose history already contains unsigned commits does not reject those
              commits, because only the commits being introduced are checked.
            - Signing is a one-time configuration for a contributor rather than a per-commit step.
              A key registered with the account and a configured `commit.gpgsign` make every
              subsequent commit signed, and commits authored through GitHub's web interface, along
              with those the merge button creates, are signed by GitHub already.
            - The provenance of a change is not otherwise recoverable after the fact. A repository
              that discovers a commit it did not expect can determine who pushed it from the audit
              log only while that log is retained, whereas a signature remains part of the commit.

            ## Reasons to Override this Default

            - The project accepts contributions from an actor that cannot sign, such as a
              self-hosted runner, a release script, or a bot pushing with a token rather than a
              key, in which case the rule blocks the automation rather than an unverified human.
            - The project's contributors cannot be expected to configure signing, such as a course
              repository or a repository accepting occasional external patches, where the rule
              turns a first contribution into a key-management exercise.
            - The repository mirrors or imports a history produced elsewhere, whose commits were
              signed by keys the repository's contributors do not hold, or were never signed at all.

            Note that the rule interacts with how a pull request is merged. GitHub evaluates
            mergeability against a test merge commit and checks the commits it introduces, so an
            unsigned commit on the head branch blocks a squash merge even though GitHub would sign
            the squash commit it produces. Such a pull request cannot be merged until the head
            branch is rewritten with signed commits or someone with bypass permission merges it.

            Note also that the rule accepts a signature GitHub can verify rather than one made by a
            particular key. A contributor who has enabled vigilant mode has commits marked
            "Partially verified" accepted, and the rule constrains who can be shown to have written
            a commit rather than what the commit contains.
            """,
        )

        if signed_commits_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["branch"])

            action = "Check" if acceptable_value else "Clear"

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Rules settings]({repository_url}/settings/rules) page.
                2) Click the name of the ruleset that targets `{branch_name}`.
                3) {action} the **Require signed commits** checkbox in the **Branch rules** section.
                4) Click the **Save changes** button at the bottom of the page.

                See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-signed-commits)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{signed_commits_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
