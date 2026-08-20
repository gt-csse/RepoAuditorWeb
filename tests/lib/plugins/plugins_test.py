import pytest

from RepoAuditorWeb.lib.plugins import community_standards_plugin, github_plugin, scientific_software_plugin
from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubModule
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
            False,
            ["skip", "url", "pat", "branch"],
        ),
        (
            community_standards_plugin,
            CommunityStandardsModule,
            "CommunityStandards",
            "Validates files that are considered community standards.",
            True,
            ["include", "one", "two"],
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
                "skip": (bool, False),
                "url": (str, None),
                "pat": (str | None, None),
                "branch": (str | None, None),
            },
        ),
        (CommunityStandardsModule, {"include": (bool, False), "one": (int, 10), "two": (str, "2")}),
        (ScientificSoftwareModule, {"include": (bool, False), "five": (int, 50), "six": (bool, False)}),
    ],
)
def test_GetParameters(module_type, expected):
    parameters = module_type().GetParameters()

    assert {k: (v.type, v.default) for k, v in parameters.items()} == expected
    assert all(param.info is not None for param in parameters.values())


# ----------------------------------------------------------------------
# Modules that have no data of their own pass their arguments straight through to their queries.
@pytest.mark.parametrize("module_type", [CommunityStandardsModule, ScientificSoftwareModule])
def test_GetModuleData(module_type):
    arguments: dict[str | None, dict[str, object]] = {None: {"include": True}}

    assert module_type().GetModuleData(arguments) is arguments


# ----------------------------------------------------------------------
@pytest.mark.parametrize("module_type", [CommunityStandardsModule, ScientificSoftwareModule])
def test_GetModuleDataNotIncluded(module_type):
    assert module_type().GetModuleData({None: {"include": False}}) is None
