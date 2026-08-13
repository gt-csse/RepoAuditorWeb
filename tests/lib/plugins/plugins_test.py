import pytest

from RepoAuditorWeb.lib.plugins import community_standards_plugin, github_plugin, scientific_software_plugin
from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule
from RepoAuditorWeb.lib.plugins.scientific_software_impl.module import ScientificSoftwareModule


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("plugin", "module_type", "name", "description", "parameter_names"),
    [
        (
            github_plugin,
            GitHubModule,
            "GitHub",
            "Validates GitHub configuration settings.",
            ["three", "four"],
        ),
        (
            community_standards_plugin,
            CommunityStandardsModule,
            "CommunityStandards",
            "Validates files that are considered community standards.",
            ["one", "two"],
        ),
        (
            scientific_software_plugin,
            ScientificSoftwareModule,
            "ScientificSoftware",
            "Validates files that are required for scientific software.",
            ["five", "six"],
        ),
    ],
)
def test_GetModule(plugin, module_type, name, description, parameter_names):
    module = plugin.GetModule()

    assert isinstance(module, module_type)
    assert module.name == name
    assert module.description == description
    assert module.requires_explicit_include is True
    assert list(module.GetParameters().keys()) == parameter_names


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("module_type", "expected"),
    [
        (GitHubModule, {"three": (int, 30), "four": (str, "4")}),
        (CommunityStandardsModule, {"one": (int, 10), "two": (str, "2")}),
        (ScientificSoftwareModule, {"five": (int, 50), "six": (bool, False)}),
    ],
)
def test_GetParameters(module_type, expected):
    parameters = module_type().GetParameters()

    assert {k: (v.type, v.default) for k, v in parameters.items()} == expected
    assert all(param.info is not None for param in parameters.values())
