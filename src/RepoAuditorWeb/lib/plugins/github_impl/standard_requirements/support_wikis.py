import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class SupportWikisRequirement(Requirement):
    """Validates whether the repository's wiki is enabled; wiki content lives in a separate repository that is not versioned alongside the code."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "SupportWikis",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "require": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the repository's wiki is enabled."),
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
        has_wiki_value = cast(dict, query_data["response"]).get("has_wiki", False)
        acceptable_value = cast(bool, requirement_data["require"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository's wiki is disabled, which matches
            the state of a newly created repository.

            ## Reasons for this Default

            - Wiki content is stored in a separate git repository (`<repository>.wiki.git`) rather than
              alongside the code, so it is not part of any commit, branch, tag, or release. A change
              cannot be reviewed with the code it documents, and documentation for a released version
              cannot be recovered by checking out that release.
            - The wiki has no pull request support, so edits land without review. Documentation kept in
              the repository is subject to the same review and status checks as the code.
            - Wiki content is not copied when the repository is forked or generated from a template, so
              contributors working from a fork lose the documentation.
            - The wiki is a distinct search surface (`type=Wikis`) and is excluded from code search, and
              search engines index only wikis belonging to repositories with 500 or more stars that
              also prevent public editing. Documentation placed there is harder to find than the same
              content in the repository.
            - Enabling the feature without populating it presents contributors with a documentation
              location that competes with the repository, which invites the two to diverge.

            ## Reasons to Override this Default

            - The project wants documentation that contributors can edit without cloning the repository
              or opening a pull request, which is the wiki's purpose.
            - The documentation is not tied to a specific version of the code (for example, meeting
              notes, a roadmap, or troubleshooting notes), so keeping it out of the repository's
              history is an advantage rather than a cost.

            Note that disabling the wiki hides existing content rather than erasing it; re-enabling the
            feature restores the previous pages. Also note that for a public repository, editing is
            restricted to collaborators by default and the wiki has a soft limit of 5,000 files.
            """,
        )

        if has_wiki_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Features** section.
                3) {action} the **Wikis** checkbox.

                See [Disabling wikis](https://docs.github.com/en/communities/documenting-your-project-with-wikis/disabling-wikis)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{has_wiki_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
