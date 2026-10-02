from RepoAuditorWeb.lib.plugins.scientific_software_impl.module import ScientificSoftwareModule


# ----------------------------------------------------------------------
def test_Construct():
    module = ScientificSoftwareModule()

    assert module.name == "ScientificSoftware"
    assert module.description == "Validates files that are required for scientific software."
    assert [query.name for query in module.queries] == ["Scientific Software"]
