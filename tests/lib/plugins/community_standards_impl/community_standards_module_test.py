from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule


# ----------------------------------------------------------------------
def test_Construct():
    module = CommunityStandardsModule()

    assert module.name == "CommunityStandards"
    assert module.description == "Validates files that are considered community standards."
    assert [query.name for query in module.queries] == ["Community Standards"]
