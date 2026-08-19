from typing import override

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.query import Query
from RepoAuditorWeb.lib.requirement import Requirement


# ----------------------------------------------------------------------
class MyRequirement(Requirement):
    @override
    def Evaluate(self, query_results: dict) -> bool:
        return True

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {}


# ----------------------------------------------------------------------
def test_Construct():
    requirements: list[Requirement] = [MyRequirement("MyRequirement", "My requirement description.")]
    query = Query("MyName", requirements)

    assert query.name == "MyName"
    assert query.requirements is requirements


# ----------------------------------------------------------------------
def test_NoRequirements():
    assert Query("MyName", []).requirements == []
