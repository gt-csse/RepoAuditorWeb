from typing import override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.github_impl.classic_branch_protection_query import (
    ClassicBranchProtectionQuery,
)
from RepoAuditorWeb.lib.plugins.github_impl.default_branch_query import DefaultBranchQuery
from RepoAuditorWeb.lib.plugins.github_impl.ruleset_query import RulesetQuery
from RepoAuditorWeb.lib.plugins.github_impl.standard_query import StandardQuery
from RepoAuditorWeb.lib.plugins.github_impl.team_size import TeamSize
from RepoAuditorWeb.lib.plugins.shared.github_session import GitHubSession
from RepoAuditorWeb.lib.plugins.shared.repository_arguments import (
    GetRepositoryParameters,
    ResolveRepositoryArguments,
)


# ----------------------------------------------------------------------
class GitHubModule(Module):
    """Module for validating GitHub repository configuration settings."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "GitHub",
            "Validates GitHub configuration settings.",
            [
                StandardQuery(),
                DefaultBranchQuery(),
                RulesetQuery(),
                ClassicBranchProtectionQuery(),
            ],
            requires_explicit_include=True,
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            **GetRepositoryParameters(),
            "team_size": TyperParameter(
                TeamSize,
                TeamSize.Small,
                OptionInfo(help=TeamSize.__doc__),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self,
        arguments: dict[str | None, dict[str, object]],
    ) -> dict[str | None, dict[str, object]]:
        module_data = arguments.get(None, {})
        repository_arguments = ResolveRepositoryArguments(module_data)

        arguments[None] = {
            "session": GitHubSession(repository_arguments.url, repository_arguments.pat),
            "branch": repository_arguments.branch,
            "team_size": TeamSize(module_data.get("team_size") or TeamSize.Small),
        }

        return arguments
