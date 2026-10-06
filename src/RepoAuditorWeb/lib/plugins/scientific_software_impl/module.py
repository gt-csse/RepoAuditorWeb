from RepoAuditorWeb.lib.plugins.scientific_software_impl.scientific_software_query import (
    ScientificSoftwareQuery,
)
from RepoAuditorWeb.lib.plugins.shared.repository_module import RepositoryModule


# ----------------------------------------------------------------------
class ScientificSoftwareModule(RepositoryModule):
    """Module for validating the existence of repository files that are required for scientific software."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "ScientificSoftware",
            "Validates files that are required for scientific software.",
            [
                ScientificSoftwareQuery(),
            ],
        )
