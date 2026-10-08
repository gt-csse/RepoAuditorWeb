import textwrap

from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import FileExistsRequirement


# ----------------------------------------------------------------------
class DocumentationRequirement(FileExistsRequirement):
    """Validates that a documentation directory exists in the root of the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Documentation",
            # `vignettes` is where R packages store long-form documentation.
            ["docs", "doc", "documentation", "vignettes"],
            ["."],
            textwrap.dedent(
                """\
                Add a `docs` directory to the root of the repository that documents the software's core
                functionality, such as API documentation generated from the source code
                (for example, with [Sphinx](https://www.sphinx-doc.org/), [MkDocs](https://www.mkdocs.org/),
                [Documenter.jl](https://documenter.juliadocs.org/), or [pkgdown](https://pkgdown.r-lib.org/)).
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a docs, doc, documentation, or vignettes directory
                exists in the root of the repository.

                ## Reasons for this Default

                - The JOSS review checklist asks whether the core functionality of the software is
                  documented to a satisfactory level, such as through API method documentation.
                - JOSS papers are not permitted to contain API documentation, so it must be provided
                  with the software.

                ## Reasons to Override this Default

                - The documentation is generated entirely from the source code, or is maintained in a
                  separate repository or wiki that the README links to.
                - The software is small enough that the README fully documents its functionality.
                """,
            ),
            is_directory=True,
        )
