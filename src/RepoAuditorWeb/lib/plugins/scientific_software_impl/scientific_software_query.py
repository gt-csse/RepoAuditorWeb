from RepoAuditorWeb.lib.plugins.scientific_software_impl.requirements.citation import CitationRequirement
from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import ClonedRepositoryQuery


# ----------------------------------------------------------------------
class ScientificSoftwareQuery(ClonedRepositoryQuery):
    """Query with requirements that check for files commonly expected in scientific software repositories."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Scientific Software",
            [
                CitationRequirement(),
            ],
        )
