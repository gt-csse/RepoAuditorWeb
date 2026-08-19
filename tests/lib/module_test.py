from typing import override

import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
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
class MyOtherRequirement(MyRequirement):
    """Distinct class name, so duplicate-name errors assert which class landed in which slot."""


# ----------------------------------------------------------------------
class MyModule(Module):
    def __init__(
        self,
        *args,
        parameters: dict[str, TyperParameter] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.parameters = (
            {"value": TyperParameter(int, 10, OptionInfo(help="Value"))} if parameters is None else parameters
        )

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return self.parameters


# ----------------------------------------------------------------------
def test_Construct():
    module = MyModule("MyName", "My description.", [])

    assert module.name == "MyName"
    assert module.description == "My description."
    assert module.queries == []
    assert module.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_Queries():
    queries = [Query("MyQuery", [MyRequirement("MyRequirement", "My requirement description.")])]

    assert MyModule("MyName", "My description.", queries).queries is queries


# ----------------------------------------------------------------------
def test_RequiresExplicitInclude():
    module = MyModule("MyName", "My description.", [], requires_explicit_include=True)

    assert module.requires_explicit_include is True


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = MyModule("MyName", "My description.", []).GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 10


# ----------------------------------------------------------------------
def test_GetParametersSkip():
    parameter = MyModule("MyName", "My description.", []).GetParameters()["skip"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Skip 'MyName' module in the run."


# ----------------------------------------------------------------------
def test_GetParametersInclude():
    parameter = MyModule(
        "MyName",
        "My description.",
        [],
        requires_explicit_include=True,
    ).GetParameters()["include"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Include 'MyName' module in the run."


# ----------------------------------------------------------------------
def test_GetParametersIncludeIsExclusiveWithSkip():
    parameters = MyModule("MyName", "My description.", [], requires_explicit_include=True).GetParameters()

    assert list(parameters.keys()) == ["include", "value"]


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("reserved_name", "requires_explicit_include"),
    [("skip", False), ("include", True)],
)
def test_ErrorReservedParameterName(reserved_name, requires_explicit_include):
    module = MyModule(
        "MyName",
        "My description.",
        [],
        parameters={reserved_name: TyperParameter(int, 10, OptionInfo(help="Value"))},
        requires_explicit_include=requires_explicit_include,
    )

    with pytest.raises(
        ValueError,
        match=f"Parameter '{reserved_name}' is reserved by Module and may not be used.",
    ):
        module.GetParameters()


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("unreserved_name", "requires_explicit_include", "expected_keys"),
    [
        ("include", False, ["skip", "include"]),
        ("skip", True, ["include", "skip"]),
    ],
)
def test_ParameterNamesAreOnlyReservedWhenTheyAreUsed(
    unreserved_name, requires_explicit_include, expected_keys
):
    parameters = MyModule(
        "MyName",
        "My description.",
        [],
        parameters={unreserved_name: TyperParameter(int, 10, OptionInfo(help="Value"))},
        requires_explicit_include=requires_explicit_include,
    ).GetParameters()

    assert list(parameters.keys()) == expected_keys


# ----------------------------------------------------------------------
def test_UniqueRequirementNamesAcrossQueries():
    queries = [
        Query("Query1", [MyRequirement("Requirement1", "Description 1.")]),
        Query("Query2", [MyRequirement("Requirement2", "Description 2.")]),
    ]

    assert MyModule("MyName", "My description.", queries).queries is queries


# ----------------------------------------------------------------------
def test_ErrorDuplicateRequirementNameInSameQuery():
    queries = [
        Query(
            "MyQuery",
            [
                MyRequirement("MyRequirement", "Description 1."),
                MyOtherRequirement("MyRequirement", "Description 2."),
            ],
        ),
    ]

    with pytest.raises(ValueError) as exc_info:
        MyModule("MyName", "My description.", queries)

    assert str(exc_info.value) == (
        "The requirement name 'MyRequirement' is used in both 'MyRequirement' and 'MyOtherRequirement'."
        " Requirement names must be unique across all queries in a module."
    )


# ----------------------------------------------------------------------
def test_ErrorDuplicateRequirementNameAcrossQueries():
    queries = [
        Query("Query1", [MyRequirement("MyRequirement", "Description 1.")]),
        Query("Query2", [MyOtherRequirement("MyRequirement", "Description 2.")]),
    ]

    with pytest.raises(ValueError) as exc_info:
        MyModule("MyName", "My description.", queries)

    assert str(exc_info.value) == (
        "The requirement name 'MyRequirement' is used in both 'MyRequirement' and 'MyOtherRequirement'."
        " Requirement names must be unique across all queries in a module."
    )


# ----------------------------------------------------------------------
def test_ErrorAbstract():
    with pytest.raises(TypeError):
        Module("MyName", "My description.", [])
