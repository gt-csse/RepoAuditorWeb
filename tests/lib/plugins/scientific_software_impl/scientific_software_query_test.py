from RepoAuditorWeb.lib.plugins.scientific_software_impl.scientific_software_query import (
    ScientificSoftwareQuery,
)


# ----------------------------------------------------------------------
def test_Construct():
    query = ScientificSoftwareQuery()

    assert query.name == "Scientific Software"
    assert [requirement.name for requirement in query.requirements] == ["Citation"]
