import textwrap

from enum import StrEnum
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class Values(StrEnum):
    """Enumeration of possible values for the DescriptionRequirement."""

    Populated = "populated"
    AllowEmpty = "allow_empty"
    Empty = "empty"


# ----------------------------------------------------------------------
class DescriptionRequirement(Requirement):
    """Requirement to validate a repository's description."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Description",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "value": TyperParameter(
                Values,
                Values.Populated,
                OptionInfo(help="How to verify the repository description."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        response = cast(dict, query_data["response"])
        value = requirement_data["value"]

        action = None

        if value == Values.Populated:
            if response.get("description"):
                result = EvaluateResultValue.Success
                context = None
            else:
                result = EvaluateResultValue.Error
                context = "The repository description is empty."
                action = "Enter a description in the **Description** text box."
        elif value == Values.AllowEmpty:
            result = EvaluateResultValue.Success
            context = None
        elif value == Values.Empty:
            if response.get("description"):
                result = EvaluateResultValue.Error
                context = "The repository description is populated."
                action = "Clear the contents of the **Description** text box."
            else:
                result = EvaluateResultValue.Success
                context = None
        else:
            assert False, value  # noqa: B011, PT015  # pragma: no cover

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that the repository has a description.

            ## Reasons for this Default

            - A repository search with no qualifier matches against the name, the description, and the
              topics, but not the contents of the README. An empty description therefore removes one of
              the three fields by which the repository can be found.
            - The description is what accompanies the repository in listings and search results, so it
              is what someone reads when deciding whether to open the repository at all.

            ## Reasons to Override this Default

            - The repository is not intended to be discovered, and describing its purpose in a field
              that feeds search works against that (`empty`).
            - The repository's name is self-explanatory, or the audience already knows what the
              repository is for, so requiring a description adds no value (`allow_empty`).
            """,
        )

        resolution = None

        if action is not None:
            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [home]({repository_url}) page.
                2) Click the **Edit** button (or the gear icon) next to the **About** section.
                3) {action}
                4) Click the **Save changes** button.

                See [About repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories)
                for more information.
                """,
            )

        return EvaluateResult(result, context, resolution, rationale, self)
