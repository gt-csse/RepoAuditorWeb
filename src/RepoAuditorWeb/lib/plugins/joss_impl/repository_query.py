from typing import override

from RepoAuditorWeb.lib.plugins.joss_impl.documents import FindPaper, FindReadme
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.contributing import ContributingRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.documentation import (
    DocumentationRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.example_usage import (
    ExampleUsageRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.installation import (
    InstallationRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper import PaperRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_length import (
    PaperLengthRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_metadata import (
    PaperMetadataRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_references import (
    PaperReferencesRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_sections import (
    PaperSectionsRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.statement_of_need import (
    StatementOfNeedRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.tests import AutomatedTestsRequirement
from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import (
    ClonedRepositoryQuery,
    GetRepositoryDirectory,
)


# ----------------------------------------------------------------------
class RepositoryQuery(ClonedRepositoryQuery):
    """Query with requirements that inspect the documentation, tests, and paper within the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Repository",
            [
                StatementOfNeedRequirement(),
                InstallationRequirement(),
                ExampleUsageRequirement(),
                DocumentationRequirement(),
                AutomatedTestsRequirement(),
                ContributingRequirement(),
                PaperRequirement(),
                PaperMetadataRequirement(),
                PaperSectionsRequirement(),
                PaperLengthRequirement(),
                PaperReferencesRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        query_data = super().GetQueryData(module_data)
        assert query_data is not None

        repo_dir = GetRepositoryDirectory(query_data)

        # CleanupQueryData is only invoked for returned query data, so the clone is removed here on failure.
        try:
            query_data["readme"] = FindReadme(repo_dir)
            query_data["paper"] = FindPaper(repo_dir)
        except BaseException:
            self.CleanupQueryData(query_data)
            raise

        return query_data
