import textwrap

from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class CitationRequirement(FileExistsRequirement):
    """Validates that a CITATION or CITATIONS file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Citation",
            ["CITATION", "CITATIONS"],
            # `inst` is where R packages store their CITATION file.
            [".", "inst"],
            textwrap.dedent(
                """\
                Add a `CITATION.cff` file to the root of the repository. The file should describe how to cite the software, including its title, authors, version, release date, and any DOI or associated publication.

                See [About CITATION files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) for more information.
                """
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a CITATION or CITATIONS file exists in the repository.

                ## Reasons for this Default

                - Researchers who use the software need to know how to cite it; without explicit
                  instructions, citations are often omitted or inconsistent.
                - Consistent citations allow the authors to receive credit for their work and allow
                  funders to measure the software's impact.
                - GitHub displays a "Cite this repository" link for `CITATION.cff` files in the
                  repository root, and services such as Zenodo use the file to populate archive metadata.

                ## Reasons to Override this Default

                - The software is not intended to be used or cited in research, such as a personal,
                  mirrored, or archived repository.
                - Citation information is provided elsewhere, such as in the documentation of a parent
                  project that links to this repository.
                """
            ),
        )
