from RepoAuditorWeb.lib.plugins.joss_impl.github_query import GitHubQuery
from RepoAuditorWeb.lib.plugins.joss_impl.repository_query import RepositoryQuery
from RepoAuditorWeb.lib.plugins.shared.repository_module import RepositoryModule


# ----------------------------------------------------------------------
class JOSSModule(RepositoryModule):
    """Module for validating the items in the JOSS review checklist that can be evaluated automatically."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "JOSS",
            "Validates the Journal of Open Source Software (JOSS) review checklist items that can be evaluated automatically.",
            [
                GitHubQuery(),
                RepositoryQuery(),
            ],
        )
