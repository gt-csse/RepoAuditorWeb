from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.code_of_conduct import (
    CodeOfConductRequirement,
)
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.contributing import (
    ContributingRequirement,
)
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.issue_template import (
    IssueTemplateRequirement,
)
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.license import LicenseRequirement
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.pull_request_template import (
    PullRequestTemplateRequirement,
)
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.readme import ReadmeRequirement
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.security import SecurityRequirement
from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import ClonedRepositoryQuery


# ----------------------------------------------------------------------
class CommunityStandardsQuery(ClonedRepositoryQuery):
    """Query with requirements that check for repository Community Standards files (as defined by GitHub)."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Community Standards",
            [
                ReadmeRequirement(),
                CodeOfConductRequirement(),
                ContributingRequirement(),
                LicenseRequirement(),
                SecurityRequirement(),
                IssueTemplateRequirement(),
                PullRequestTemplateRequirement(),
            ],
        )
