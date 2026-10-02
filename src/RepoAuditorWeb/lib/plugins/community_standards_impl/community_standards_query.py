import textwrap

from tempfile import TemporaryDirectory
from typing import cast, override
from urllib.parse import urlparse

from RepoAuditorWeb.lib.query import Query
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
from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.readme import ReadmeRequirement


# ----------------------------------------------------------------------
class CommunityStandardsQuery(Query):
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
                IssueTemplateRequirement(),
            ],
        )

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        module_data["repo_dir"] = TemporaryDirectory()

        url = module_data["url"]
        assert isinstance(url, str), (url, type(url))

        pat = module_data["pat"]

        if pat is not None:
            assert isinstance(pat, str), (pat, type(pat))

            passed_url = urlparse(url)
            url = f"https://{pat}@{passed_url.netloc}{passed_url.path}"

        # Import git.Repo here so that it is only imported if the CommunityStandards plugin is requests
        from git import Repo  # noqa: PLC0415

        try:
            Repo.clone_from(url, module_data["repo_dir"].name, branch=module_data["branch"], depth=1)
        except Exception as ex:
            # git output includes the clone url, which embeds the PAT.
            error = str(ex) if pat is None else str(ex).replace(pat, "***")

            msg = textwrap.dedent(
                f"""\
                An error occurred while attempting to clone the target repository.

                If you are auditing a private repository, {
                    "please ensure your PAT has access to the repository."
                    if pat is not None
                    else "please provide a PAT with access to the repository."
                }

                Error: {error}
                """,
            )

            # The original exception is not chained when a PAT is present, as tracebacks would display the PAT within its message.
            raise RuntimeError(msg) from (ex if pat is None else None)

        return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        cast(TemporaryDirectory, query_data["repo_dir"]).cleanup()
