import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class ProtectedMainlineBranchRequirement(Requirement):
    """Validates whether the default branch is protected by a branch protection rule or a ruleset, which blocks force pushes and deletion."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "ProtectedMainlineBranch",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the branch to be protected, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the default branch is not protected."),
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
        protected_value = cast(bool, cast(dict, query_data["response"]).get("protected", False))
        acceptable_value = not cast(bool, requirement_data["prohibit"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the default branch is protected. GitHub reports
            the branch as protected when a branch protection rule or a ruleset targets it, so either
            mechanism satisfies this requirement.

            ## Reasons for this Default

            - An unprotected default branch accepts a force push from anyone with write access, which
              replaces history that existing clones and published references already depend on. The
              commits the push abandoned are no longer reachable, so recovering them requires knowing
              that they existed.
            - Protecting the branch is what makes the rest of the repository's review configuration
              binding. Settings such as the merge methods and auto-merge describe how a pull request
              may be merged, but they do not require that a change arrive through one; a direct push
              bypasses them entirely.
            - The default branch is the branch a clone checks out, the base branch proposed for new
              pull requests, and the branch consumers reference by name, so it is the branch where
              rewritten history is most widely observed.
            - Protection is the mechanism the rules worth having later are attached to, including
              required reviews, status checks, and linear history. This requirement establishes that
              mechanism rather than any particular rule.

            ## Reasons to Override this Default

            - The repository is private and owned by an account on a plan that offers neither branch
              protection rules nor rulesets for private repositories, in which case protecting the
              branch is a purchasing decision rather than a configuration one.
            - The repository is a scratch, mirror, or generated repository whose default branch is
              rewritten by design, where blocking force pushes prevents the repository from serving
              its purpose.
            - Protection is enforced where GitHub does not report it, such as a pre-receive hook on
              an Enterprise Server instance, so the branch is governed while this value remains
              false.

            Note that this requirement establishes only that the branch is protected, not what the
            protection requires. A rule that targets the branch and enables nothing beyond the
            defaults still reports the branch as protected while permitting unreviewed direct pushes.

            Note also that protection does not by itself constrain everyone. A classic branch
            protection rule does not apply to those who can bypass it unless **Do not allow
            bypassing the above settings** is enabled, and a ruleset does not apply to the actors
            named in its bypass list.
            """,
        )

        if protected_value != acceptable_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url
            branch_name = cast(str, query_data["default_branch"])

            rules_link = f"[Rules settings]({repository_url}/settings/rules)"
            branches_link = f"[Branches settings]({repository_url}/settings/branches)"

            open_rules_step = f"Open the repository's {rules_link} page."

            if acceptable_value:
                steps = [
                    open_rules_step,
                    "Click the **New ruleset** button, then click **New branch ruleset**.",
                    f"Enter `'{branch_name}' - ruleset` in the **Ruleset name** field.",
                    "Set the enforcement status to **Active**.",
                    "Click the **Add target** button in the **Target branches** section, then choose **Include default branch**.",
                    "Click the **Create** button at the bottom of the page.",
                ]

                trailer = textwrap.dedent(
                    f"""\

                    A classic branch protection rule whose branch name pattern matches
                    `{branch_name}` is an equivalent alternative, created from the repository's
                    {branches_link} page via the **Add classic branch protection rule** button.
                    """,
                )

                documentation_name = "Creating"
            else:
                steps = [
                    open_rules_step,
                    f"Delete each ruleset that targets `{branch_name}`, or set its enforcement status to **Disabled**.",
                    f"Open the repository's {branches_link} page.",
                    f"Delete each classic branch protection rule whose branch name pattern matches `{branch_name}`.",
                ]

                trailer = ""
                documentation_name = "Managing"

            documentation_url = f"https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/{documentation_name.lower()}-rulesets-for-a-repository"

            resolution = "".join(
                [
                    *(f"{index}) {step}\n" for index, step in enumerate(steps, start=1)),
                    trailer,
                    f"\nSee [{documentation_name} rulesets for a repository]({documentation_url})\nfor more information.\n",
                ],
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{protected_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
