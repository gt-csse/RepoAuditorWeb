from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.statement_of_need import (
    StatementOfNeedRequirement,
)


# ----------------------------------------------------------------------
def test_Construct():
    requirement = StatementOfNeedRequirement()

    assert requirement.name == "StatementOfNeed"
    assert (
        requirement.description
        == "Validates that the README contains a section describing the problems the software solves."
    )
    assert requirement.requires_explicit_include is False
    assert requirement.GetParameters()["pattern"].default == r"statement of need|motivation|purpose|\bwhy\b"
