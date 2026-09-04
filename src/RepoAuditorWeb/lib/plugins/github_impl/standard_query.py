from typing import cast, override

import requests

from RepoAuditorWeb.lib.plugins.github_impl.default_branch_requirement import DefaultBranchRequirement
from RepoAuditorWeb.lib.plugins.github_impl.description_requirement import DescriptionRequirement
from RepoAuditorWeb.lib.plugins.github_impl.license_requirement import LicenseRequirement
from RepoAuditorWeb.lib.plugins.github_impl.template_requirement import TemplateRequirement
from RepoAuditorWeb.lib.plugins.github_impl.web_commit_signoff_requirement import WebCommitSignoffRequirement
from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class StandardQuery(Query):
    """Query with Requirements that operate on basic GitHub repository data."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Standard",
            [
                # metadata
                DescriptionRequirement(),
                LicenseRequirement(),
                # settings page
                TemplateRequirement(),
                WebCommitSignoffRequirement(),
                DefaultBranchRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        response = cast(requests.Session, module_data["session"]).get("")

        response.raise_for_status()
        response = response.json()

        module_data["response"] = response
        return module_data
