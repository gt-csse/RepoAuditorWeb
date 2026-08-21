import pytest

from RepoAuditorWeb.lib.query import Query
from RepoAuditorWeb.lib.requirement import Requirement

from conftest import MyQuery, MyRequirement


# ----------------------------------------------------------------------
def test_Construct():
    requirements: list[Requirement] = [MyRequirement("MyRequirement", "My requirement description.")]
    query = MyQuery("MyName", requirements)

    assert query.name == "MyName"
    assert query.requirements is requirements


# ----------------------------------------------------------------------
def test_NoRequirements():
    assert MyQuery("MyName", []).requirements == []


# ----------------------------------------------------------------------
def test_GetQueryData():
    query_data: dict[str, object] = {"value": 10}

    assert MyQuery("MyName", [], query_data=query_data).GetQueryData({}) is query_data


# ----------------------------------------------------------------------
def test_GetQueryDataReceivesModuleData():
    query = MyQuery("MyName", [])
    module_data: dict[str, object] = {"session": object()}

    query.GetQueryData(module_data)

    assert query.module_data is module_data


# ----------------------------------------------------------------------
def test_ErrorAbstract():
    with pytest.raises(TypeError):
        Query("MyName", [])
