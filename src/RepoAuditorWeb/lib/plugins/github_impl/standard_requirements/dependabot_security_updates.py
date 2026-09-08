import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.restricted_value import (
    AccessLevel,
    GetRestrictedValue,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
# GitHub reports the setting as an object rather than a boolean so that additional state can be
# introduced without changing the shape of the response.
_ENABLED_STATUS = "enabled"


# ----------------------------------------------------------------------
class DependabotSecurityUpdatesRequirement(Requirement):
    """Validates whether Dependabot automatically opens pull requests that update dependencies with known vulnerabilities to a patched version."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "DependabotSecurityUpdates",
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
                OptionInfo(help="Require that Dependabot security updates are not enabled."),
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
            The default behavior is to require that Dependabot security updates are enabled.

            Note that this differs from the state of a newly created repository, where the setting is
            disabled.

            ## Reasons for this Default

            - A dependency with a published advisory is a vulnerability the project already has, and
              the patched version already exists. What remains is the work of noticing the advisory
              and applying the update, which is what this setting performs.
            - An alert states that a problem exists; a pull request states what to do about it. The
              difference matters because the alert is read by whoever thinks to look at the security
              tab, while the pull request arrives where the project already reviews changes.
            - Advisories are published on the ecosystem's schedule rather than the project's, so a
              project that updates dependencies only when it happens to touch them is exposed for
              however long it is between such occasions. Automating the response removes that
              interval.
            - The change is proposed rather than applied. It arrives as a pull request against the
              default branch, subject to the same review and status checks as any other change, so
              enabling the setting delegates the noticing rather than the deciding.
            - The update is the smallest one that resolves the advisory, so the pull request is
              usually a version bump rather than a migration, and the cost of reviewing it is
              correspondingly small.

            ## Reasons to Override this Default

            - The project prefers to choose which alerts produce pull requests. Dependabot attempts
              to open one for every open alert that has a patch available, which on a large or
              long-neglected dependency set is a volume of pull requests that is read as noise and
              then ignored. Auto-triage rules, applied with the setting disabled, are the documented
              alternative.
            - Pull requests trigger workflows, so on a project with expensive continuous integration
              the automated updates consume Actions minutes on a schedule the project does not
              control.
            - Dependencies are managed outside the repository, such as by a vendored tree, an
              internal mirror, or a tool that resolves versions centrally, in which case a pull
              request that edits a manifest proposes a change the project cannot merge.

            Note that the setting depends on the dependency graph and Dependabot alerts; enabling
            Dependabot enables the dependency graph if it is not already on.

            Note also that updates are raised against the default branch only, and only for
            dependencies declared in a manifest or lock file, so a repository whose dependencies are
            detected but not declared receives alerts without corresponding pull requests. Not every
            ecosystem supports security updates, and a repository with no manifest has nothing for
            the setting to act on.
            """,
        )

        # Unlike the other restricted settings, 'security_and_analysis' requires admin access rather
        # than push access, and reports the setting as a nested status string rather than a boolean.
        status_value = GetRestrictedValue(
            module,
            self,
            query_data,
            ("security_and_analysis", "dependabot_security_updates", "status"),
            "security and analysis settings",
            AccessLevel.Admin,
        )

        if isinstance(status_value, EvaluateResult):
            return status_value

        dependabot_security_updates_value = status_value == _ENABLED_STATUS

        if dependabot_security_updates_value != acceptable_value:
            action = "Enable" if acceptable_value else "Disable"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Advanced Security settings]({repository_url}/settings/security_analysis) page.
                2) Scroll to the **Dependabot security updates** row.
                3) Click the **{action}** button.
                4) Click the **Save changes** button at the bottom of the page.

                See [Configuring Dependabot security updates](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-security-updates)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{dependabot_security_updates_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
