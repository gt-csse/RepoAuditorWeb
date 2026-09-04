import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class WebCommitSignoffRequirement(Requirement):
    """Validates whether contributors must sign off on commits made through GitHub's web interface; commits made from the command line are unaffected."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "WebCommitSignoff",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(
                    help="Require that contributors must sign off on web-based commits.",
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
        web_commit_signoff_value = cast(
            bool, cast(dict, query_data["response"]).get("web_commit_signoff_required", False)
        )
        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to not require contributors to sign off on web-based commits. When
            the requirement is enabled, GitHub's web interface tells the contributor that committing
            also constitutes signing off, and appends a `Signed-off-by` trailer on their behalf.

            ## Reasons for this Default

            - The project has no signoff policy, in which case the trailer asserts a certification
              (commonly the [Developer Certificate of Origin](https://developercertificate.org/)) that
              the project does not actually require.
            - The project wants signing off to be a separate, deliberate act rather than a side effect
              of committing, because the trailer certifies that the contributor holds the rights to
              submit the change and the record is retained indefinitely.

            ## Reasons to Override this Default

            - Projects that enforce a signoff policy typically verify it with a status check that fails
              when a trailer is missing. Contributors editing through the web interface cannot pass
              `--signoff`, so the check fails after the fact and recovering from it requires rewriting
              history.
            - The trailer is the same one produced by `git commit --signoff`, so requiring it makes
              web-based commits consistent with signed-off commits made from the command line.

            Note that this requirement governs only the web interface; commits made from the command
            line are unaffected, so it does not by itself guarantee that every commit is signed off.
            """,
        )

        if web_commit_signoff_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Commits** section.
                3) {action} the **Require contributors to sign off on web-based commits** checkbox.

                See [Managing the commit signoff policy for your repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-the-commit-signoff-policy-for-your-repository)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{web_commit_signoff_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
