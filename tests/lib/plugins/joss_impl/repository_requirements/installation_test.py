from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.installation import (
    InstallationRequirement,
)


# ----------------------------------------------------------------------
def test_Construct():
    requirement = InstallationRequirement()

    assert requirement.name == "Installation"
    assert (
        requirement.description
        == "Validates that the README contains a section describing how to install the software."
    )
    assert requirement.requires_explicit_include is False
    assert (
        requirement.GetParameters()["pattern"].default
        == r"install|getting started|set ?up|requirements|dependencies"
    )
