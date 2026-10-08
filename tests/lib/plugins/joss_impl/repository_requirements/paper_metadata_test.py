import textwrap

from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_metadata import (
    PaperMetadataRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


_METADATA: dict[str, object] = {
    "title": "My Title",
    "tags": ["Python"],
    "authors": [
        {"name": "One", "affiliation": "1, 2"},
        {"given-names": "Two", "surname": "Author", "affiliation": 2},
    ],
    "affiliations": [{"name": "First", "index": 1}, {"name": "Second", "index": 2}],
    "date": "9 October 2024",
    "bibliography": "paper.bib",
}


# ----------------------------------------------------------------------
def _Evaluate(metadata: dict[str, object] | None):
    paper = Paper("paper/paper.md", "", metadata, None if metadata is not None else "No front matter.")

    return PaperMetadataRequirement().Evaluate(JOSSModule(), {"paper": paper}, {"skip": False})


# ----------------------------------------------------------------------
def test_Construct():
    requirement = PaperMetadataRequirement()

    assert requirement.name == "PaperMetadata"
    assert (
        requirement.description
        == "Validates the paper's title, tags, authors, affiliations, date, and bibliography."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_Complete():
    result = _Evaluate(_METADATA)

    assert result.result == EvaluateResultValue.Success
    assert result.context == "The metadata in `paper/paper.md` is complete."
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_MetadataError():
    result = _Evaluate(None)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The metadata in `paper/paper.md` has these problems:\n\n- No front matter."
    assert result.resolution is not None


# ----------------------------------------------------------------------
def test_Empty():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == textwrap.dedent(
        """\
        The metadata in `paper/paper.md` has these problems:

        - `title` must be a non-empty string.
        - `bibliography` must be a non-empty string.
        - `tags` must be a non-empty list.
        - `date` must be formatted as `<day> <month name> <year>`, such as `9 October 2024`.
        - `affiliations` must be a non-empty list.
        - `authors` must be a non-empty list.""",
    )


# ----------------------------------------------------------------------
def test_InvalidValues():
    result = _Evaluate(
        {
            **_METADATA,
            "title": " ",
            "date": "2024-10-09",
            "authors": [
                "Name",
                {"surname": "Two"},
                {"name": "Three", "affiliation": "1, 3"},
            ],
            "affiliations": [{"name": "First", "index": 1}, {"name": "No index"}, {"index": 3}],
        },
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == textwrap.dedent(
        """\
        The metadata in `paper/paper.md` has these problems:

        - `title` must be a non-empty string.
        - `date` must be formatted as `<day> <month name> <year>`, such as `9 October 2024`.
        - Affiliation 2 must have an `index` and a `name`.
        - Affiliation 3 must have an `index` and a `name`.
        - Author 1 must have a `name` (or a `surname`).
        - Author 2 must have an `affiliation`.
        - Author 3 references affiliation `3`, which is not defined in `affiliations`.""",
    )


# ----------------------------------------------------------------------
# YAML aliases can expand a small collection into one that exhausts memory when converted to a string.
def test_NonScalarAffiliations():
    result = _Evaluate(
        {
            **_METADATA,
            "authors": [{"name": "One", "affiliation": ["1"]}],
            "affiliations": [{"name": "First", "index": {"value": 1}}],
        },
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == textwrap.dedent(
        """\
        The metadata in `paper/paper.md` has these problems:

        - Affiliation 1 must have an `index` and a `name`.
        - Author 1 must have an `affiliation`.""",
    )
