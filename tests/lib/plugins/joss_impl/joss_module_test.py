from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule


# ----------------------------------------------------------------------
def test_Construct():
    module = JOSSModule()

    assert module.name == "JOSS"
    assert (
        module.description
        == "Validates the Journal of Open Source Software (JOSS) review checklist items that can be evaluated automatically."
    )
    assert [query.name for query in module.queries] == ["GitHub", "Repository"]
    assert module.requires_explicit_include is True
