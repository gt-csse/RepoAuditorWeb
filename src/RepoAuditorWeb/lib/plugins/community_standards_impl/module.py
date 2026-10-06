from RepoAuditorWeb.lib.plugins.community_standards_impl.community_standards_query import (
    CommunityStandardsQuery,
)
from RepoAuditorWeb.lib.plugins.shared.repository_module import RepositoryModule


# ----------------------------------------------------------------------
class CommunityStandardsModule(RepositoryModule):
    """Module for validating the existence of repository files that are considered community standards."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "CommunityStandards",
            "Validates files that are considered community standards.",
            [
                CommunityStandardsQuery(),
            ],
        )
