import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class LicenseRequirement(Requirement):
    """Validates the license GitHub detects from the repository's LICENSE file; without one, default copyright law reserves all rights to the author."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "License",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                list[str],
                ["MIT License"],
                OptionInfo(help="List of acceptable licenses for the repository."),
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
        license_value = cast(dict, query_data["response"]).get("license", {}).get("name")
        acceptable_values = cast(list[str], requirement_data["value"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository is licensed under the MIT License.

            ## Reasons for this Default

            - Without a license, default copyright law applies and the author retains all rights; no
              one may reproduce, distribute, or create derivative works from the code. Publishing a
              repository does not by itself grant anyone permission to use it.
            - The MIT License is short, permissive, and widely recognized, which minimizes the review
              burden on anyone deciding whether they may adopt the code.

            ## Reasons to Override this Default

            - The organization standardizes on a different license.
            - The repository incorporates code under a license that requires derived works to carry the
              same terms (for example, the GNU General Public License), which the MIT License cannot
              satisfy.
            - The project intends to require that modifications be shared, which a permissive license
              does not do.

            Note that GitHub identifies the license by comparing the `LICENSE` file against a list of
            known licenses, so an accurate copy of the chosen license is what causes it to be reported.
            """,
        )

        if license_value is None or license_value not in acceptable_values:
            acceptable_values_str = ", ".join(f"'{v}'" for v in acceptable_values)

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [home]({repository_url}) page.
                2) Add or replace the repository's `LICENSE` file with the text of one of these licenses: {acceptable_values_str}.
                3) Commit the change to the repository's default branch.

                GitHub detects the license from the `LICENSE` file's contents, so the file must contain
                the license text verbatim.

                See [Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
                for more information.
                """,
            )

            context = (
                "No license value was set."
                if license_value is None
                else f"The license '{license_value}' is not in the list of acceptable licenses ({acceptable_values_str})."
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
