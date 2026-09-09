import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.restricted_value import (
    AccessLevel,
    ENABLED_STATUS,
    GetRestrictedValue,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SecretProtectionRequirement(Requirement):
    """Validates whether GitHub scans the repository's history, branches, and other content for credentials and raises an alert when one is found."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SecretProtection",
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
                OptionInfo(help="Require that secret protection is not enabled."),
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
            The default behavior is to require that secret protection is enabled.

            ## Reasons for this Default

            - A credential committed to a repository is disclosed at the moment of the push, and
              stays disclosed until it is revoked. Deleting the line does not help, because the
              commit that introduced it remains reachable, which makes finding the credential the
              part of the problem worth automating.
            - The scan covers the entire git history on all branches, along with issues, pull
              requests, discussions, and wikis, so it reports credentials that predate the setting
              being turned on rather than only those pushed afterwards.
            - Detection is by partner pattern rather than by guesswork, and GitHub notifies the
              provider that issued the credential, so a leaked token is often revoked by the
              provider before the project has read the alert.
            - Enabling the setting also brings push protection for the secret types included by
              default, which blocks the commit that would have leaked the credential; the difference
              between preventing a leak and reporting one is the cost of rotating the credential.
            - Validity checks state whether a detected credential is still live, which is what
              separates an alert that requires immediate rotation from one that documents a
              credential already revoked.
            - The setting reports rather than enforces. An alert costs the project the time to read
              it, and the credential it names was already exposed, so the setting cannot make the
              repository's position worse than it was.

            ## Reasons to Override this Default

            - The repository intentionally contains strings that resemble credentials, such as test
              fixtures, documentation examples, or revoked sample keys, and the resulting alerts
              are read as noise. Excluding paths with `secret_scanning.yml` is the narrower
              alternative to disabling the setting outright.
            - The project scans with a different tool that it already acts on, and duplicating the
              alerts across two systems means neither is treated as the authoritative one.
            - The repository is private and the organization does not hold the GitHub Secret
              Protection license the setting requires there, in which case enabling it is a
              purchasing decision rather than a configuration one.

            Note that alerts are visible only to users with write access or better, so enabling the
            setting on a public repository does not disclose the location of a credential to the
            public.

            Note also that detection is limited to the supported patterns, so the setting does not
            establish that a repository is free of credentials; a password or an internal token in a
            format no provider has registered is not detected.
            """,
        )

        # Unlike the other restricted settings, 'security_and_analysis' requires admin access rather
        # than push access, and reports the setting as a nested status string rather than a boolean.
        status_value = GetRestrictedValue(
            module,
            self,
            query_data,
            ("security_and_analysis", "secret_scanning", "status"),
            "security and analysis settings",
            AccessLevel.Admin,
        )

        if isinstance(status_value, EvaluateResult):
            return status_value

        secret_protection_value = status_value == ENABLED_STATUS

        if secret_protection_value != acceptable_value:
            action = "Enable" if acceptable_value else "Disable"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [Advanced Security settings]({repository_url}/settings/security_analysis) page.
                2) Scroll to the **Secret Protection** row.
                3) Click the **{action}** button.
                4) Confirm the change when prompted.
                5) Click the **Save changes** button at the bottom of the page.

                See [Enabling secret scanning for your repository](https://docs.github.com/en/code-security/how-tos/secure-your-secrets/detect-secret-leaks/enable-secret-scanning)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{secret_protection_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
