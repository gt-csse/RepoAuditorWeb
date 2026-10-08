import pytest

from RepoAuditorWeb.lib.plugins import (
    community_standards_plugin,
    github_plugin,
    joss_plugin,
    scientific_software_plugin,
)
from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule, TeamSize
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.scientific_software_impl.module import ScientificSoftwareModule


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("plugin", "module_type", "name", "description", "requires_explicit_include", "parameter_names"),
    [
        (
            github_plugin,
            GitHubModule,
            "GitHub",
            "Validates GitHub configuration settings.",
            True,
            ["include", "url", "pat", "branch", "team_size"],
        ),
        (
            community_standards_plugin,
            CommunityStandardsModule,
            "CommunityStandards",
            "Validates files that are considered community standards.",
            True,
            ["include", "url", "pat", "branch"],
        ),
        (
            scientific_software_plugin,
            ScientificSoftwareModule,
            "ScientificSoftware",
            "Validates files that are required for scientific software.",
            True,
            ["include", "url", "pat", "branch"],
        ),
        (
            joss_plugin,
            JOSSModule,
            "JOSS",
            "Validates the Journal of Open Source Software (JOSS) review checklist items that can be evaluated automatically.",
            True,
            ["include", "url", "pat", "branch"],
        ),
    ],
)
def test_GetModule(plugin, module_type, name, description, requires_explicit_include, parameter_names):
    module = plugin.GetModule()

    assert isinstance(module, module_type)
    assert module.name == name
    assert module.description == description
    assert module.requires_explicit_include is requires_explicit_include
    assert list(module.GetParameters().keys()) == parameter_names


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("module_type", "expected"),
    [
        (
            GitHubModule,
            {
                "include": (bool, False),
                "url": (str, None),
                "pat": (str | None, None),
                "branch": (str | None, None),
                "team_size": (TeamSize, TeamSize.Small),
            },
        ),
        (
            CommunityStandardsModule,
            {
                "include": (bool, False),
                "url": (str, None),
                "pat": (str | None, None),
                "branch": (str | None, None),
            },
        ),
        (
            ScientificSoftwareModule,
            {
                "include": (bool, False),
                "url": (str, None),
                "pat": (str | None, None),
                "branch": (str | None, None),
            },
        ),
        (
            JOSSModule,
            {
                "include": (bool, False),
                "url": (str, None),
                "pat": (str | None, None),
                "branch": (str | None, None),
            },
        ),
    ],
)
def test_GetParameters(module_type, expected):
    parameters = module_type().GetParameters()

    assert {k: (v.type, v.default) for k, v in parameters.items()} == expected
    assert all(param.info is not None for param in parameters.values())
