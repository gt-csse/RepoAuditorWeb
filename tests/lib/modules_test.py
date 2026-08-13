from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.modules import MODULES


# ----------------------------------------------------------------------
def test_AllModulesLoaded():
    assert [module.name for module in MODULES] == [
        "GitHub",
        "CommunityStandards",
        "ScientificSoftware",
    ]


# ----------------------------------------------------------------------
def test_GitHubIsFirst():
    assert MODULES[0].name == "GitHub"


# ----------------------------------------------------------------------
def test_RemainingModulesAreSorted():
    remaining = [module.name for module in MODULES[1:]]

    assert remaining == sorted(remaining)


# ----------------------------------------------------------------------
def test_Types():
    assert all(isinstance(module, Module) for module in MODULES)
