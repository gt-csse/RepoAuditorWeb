import pytest

from RepoAuditorWeb.lib.plugins import community_standards_plugin, github_plugin, scientific_software_plugin
from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule, TeamSize
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
            ["include", "five", "six"],
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
        (ScientificSoftwareModule, {"include": (bool, False), "five": (int, 50), "six": (bool, False)}),
    ],
)
def test_GetParameters(module_type, expected):
    parameters = module_type().GetParameters()

    assert {k: (v.type, v.default) for k, v in parameters.items()} == expected
    assert all(param.info is not None for param in parameters.values())


# ----------------------------------------------------------------------
# Modules that have no data of their own pass their arguments straight through to their queries.
def test_GetModuleData():
    arguments: dict[str | None, dict[str, object]] = {None: {"include": True}}

    assert ScientificSoftwareModule().GetModuleData(arguments) is arguments


# ----------------------------------------------------------------------
def test_GetModuleDataNotIncluded():
    assert ScientificSoftwareModule().GetModuleData({None: {"include": False}}) is None
