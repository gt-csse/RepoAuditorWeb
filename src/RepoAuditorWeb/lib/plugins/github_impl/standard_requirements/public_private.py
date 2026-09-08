import textwrap

from enum import StrEnum
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class Values(StrEnum):
    """Enumeration of possible values for the PublicPrivateRequirement."""

    Public = "public"
    Private = "private"
    Internal = "internal"


# ----------------------------------------------------------------------
class PublicPrivateRequirement(Requirement):
    """Validates the repository's visibility, which determines who can see the code and which GitHub features the repository is eligible for."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PublicPrivate",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # An enumeration rather than a flag so that an enterprise can require 'internal'; the
            # 'private' boolean cannot express that distinction.
            "value": TyperParameter(
                Values,
                Values.Public,
                OptionInfo(help="The required visibility of the repository."),
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
        visibility_value = cast(dict, query_data["response"]).get("visibility")
        expected_value = cast(Values, requirement_data["value"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository is public.

            ## Reasons for this Default

            - A repository that cannot be read cannot be audited, cited, reproduced, or contributed
              to by anyone outside its access list. Visibility is the setting every other
              collaboration setting depends on.
            - Features that make a project legible to outsiders are available on public repositories
              regardless of plan, but require a paid plan on private ones. The community profile,
              dependency graph, and GitHub Pages are examples; a public repository gets the full
              feature set on GitHub Free, while a private one gets a limited one.
            - GitHub Actions minutes and Packages storage are not billed for public repositories, so
              a public project's continuous integration does not consume the account's included
              allowance.
            - Only public repositories are eligible for the GitHub Archive Program, so public
              visibility is what causes the code to be preserved independently of the account that
              hosts it.
            - Forking, which is how a contributor proposes a change without write access, requires
              that the contributor can read the repository.

            ## Reasons to Override this Default

            - The code is not intended for release: it contains proprietary logic, embargoed
              research, unpublished results, or material the project does not hold the rights to
              distribute.
            - The repository is subject to a policy that forbids public disclosure, such as
              export control, a data use agreement, or an institutional review requirement.
            - The repository is not ready to be read, and a premature release would misrepresent the
              project. Note that this argues for publishing later rather than for staying private,
              since visibility can be changed at any time.
            - The organization belongs to an enterprise account and uses `internal` visibility to
              share the repository across the enterprise without exposing it publicly, in which case
              `internal` is the expected value.

            Note that visibility is a poor secrecy control applied after the fact. Making a public
            repository private does not erase what was already cloned or cached, and a secret that was
            ever committed remains in the history; such a secret must be rotated rather than hidden.

            Note also that changing visibility in either direction erases the repository's stars and
            watchers, and that making a repository public makes its Actions history and logs visible
            to everyone.
            """,
        )

        if visibility_value != expected_value:
            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Danger Zone** section.
                3) Click the **Change visibility** button.
                4) Select '{expected_value}'.
                5) Click the **I have read and understand these effects** button.
                6) Enter the repository's name to confirm, then click the button that completes the change.

                See [Setting repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
                for more information.
                """,
            )

            context = (
                "No visibility value was set."
                if visibility_value is None
                else f"The visibility is '{visibility_value}' but '{expected_value}' was expected."
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                context,
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
