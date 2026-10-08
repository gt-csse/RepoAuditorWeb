import textwrap

from datetime import datetime
from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_content_requirement import (
    PaperContentRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper


# ----------------------------------------------------------------------
class PaperMetadataRequirement(PaperContentRequirement):
    """Validates the paper's title, tags, authors, affiliations, date, and bibliography."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PaperMetadata",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require the metadata defined by the JOSS paper format.

                ## Reasons for this Default

                - JOSS requires the paper to list the authors of the software and their affiliations
                  using its format, and uses the metadata to generate the published paper and the
                  metadata deposited with Crossref.
                - Missing or malformed metadata prevents the paper from compiling, which delays the review.

                ## Reasons to Override this Default

                - The software is not being prepared for submission to JOSS.
                """,
            ),
        )

    # ----------------------------------------------------------------------
    @override
    def _EvaluatePaper(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        paper: Paper,
    ) -> EvaluateResult:
        problems = (
            [cast(str, paper.metadata_error)] if paper.metadata is None else _GetProblems(paper.metadata)
        )

        if problems:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                "\n".join(
                    [
                        f"The metadata in `{paper.path}` has these problems:",
                        "",
                        *(f"- {problem}" for problem in problems),
                    ],
                ),
                textwrap.dedent(
                    """\
                    Update the YAML front matter at the beginning of the paper to follow the
                    [example paper](https://joss.readthedocs.io/en/latest/example_paper.html). See
                    [Article metadata](https://joss.readthedocs.io/en/latest/paper.html#article-metadata)
                    for more information.
                    """,
                ),
            )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Success,
            f"The metadata in `{paper.path}` is complete.",
        )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _GetProblems(metadata: dict[str, object]) -> list[str]:
    problems: list[str] = []

    for field in ["title", "bibliography"]:
        value = metadata.get(field)

        if not isinstance(value, str) or not value.strip():
            problems.append(f"`{field}` must be a non-empty string.")

    tags = metadata.get("tags")

    if not isinstance(tags, list) or not tags:
        problems.append("`tags` must be a non-empty list.")

    date = metadata.get("date")

    if not isinstance(date, str) or not _IsValidDate(date):
        problems.append("`date` must be formatted as `<day> <month name> <year>`, such as `9 October 2024`.")

    # Affiliations are referenced by index, so their indexes are needed to validate the authors.
    affiliation_indexes: set[str] = set()
    affiliations = metadata.get("affiliations")

    if not isinstance(affiliations, list) or not affiliations:
        problems.append("`affiliations` must be a non-empty list.")
    else:
        for affiliation_index, affiliation in enumerate(affiliations, 1):
            if (
                not isinstance(affiliation, dict)
                or not _IsScalar(affiliation.get("index"))
                or "name" not in affiliation
            ):
                problems.append(f"Affiliation {affiliation_index} must have an `index` and a `name`.")
            else:
                affiliation_indexes.add(str(cast(dict[str, object], affiliation)["index"]))

    authors = metadata.get("authors")

    if not isinstance(authors, list) or not authors:
        problems.append("`authors` must be a non-empty list.")
        return problems

    for author_index, author in enumerate(authors, 1):
        if not isinstance(author, dict) or not ("name" in author or "surname" in author):
            problems.append(f"Author {author_index} must have a `name` (or a `surname`).")
            continue

        if not _IsScalar(author.get("affiliation")):
            problems.append(f"Author {author_index} must have an `affiliation`.")
            continue

        # Multiple affiliations are written as a quoted, comma-delimited string, such as "1, 2".
        problems.extend(
            f"Author {author_index} references affiliation `{index}`, which is not defined in `affiliations`."
            for index in (
                part.strip() for part in str(cast(dict[str, object], author)["affiliation"]).split(",")
            )
            if index not in affiliation_indexes
        )

    return problems


# ----------------------------------------------------------------------
def _IsScalar(value: object) -> bool:
    # Only scalars are converted to strings; YAML aliases can expand a small collection into one
    # that exhausts memory when converted.
    return isinstance(value, str | int | float)


# ----------------------------------------------------------------------
def _IsValidDate(date: str) -> bool:
    try:
        # Only the format is validated, so the time zone is irrelevant.
        datetime.strptime(date.strip(), "%d %B %Y")  # noqa: DTZ007
    except ValueError:
        return False

    return True
