from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.example_usage import (
    ExampleUsageRequirement,
)


# ----------------------------------------------------------------------
def test_Construct():
    requirement = ExampleUsageRequirement()

    assert requirement.name == "ExampleUsage"
    assert (
        requirement.description
        == "Validates that the README contains a section describing how to use the software."
    )
    assert requirement.requires_explicit_include is False
    assert (
        requirement.GetParameters()["pattern"].default
        == r"usage|example|tutorial|quick ?start|getting started|how to use"
    )
