from typing import override

import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import Requirement


# ----------------------------------------------------------------------
class MyRequirement(Requirement):
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
    def Evaluate(self, query_results: dict) -> bool:
        return query_results.get("result", False)

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return self.parameters


# ----------------------------------------------------------------------
def test_Construct():
    requirement = MyRequirement("MyName", "My description.")

    assert requirement.name == "MyName"
    assert requirement.description == "My description."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_RequiresExplicitInclude():
    requirement = MyRequirement("MyName", "My description.", requires_explicit_include=True)

    assert requirement.requires_explicit_include is True


# ----------------------------------------------------------------------
def test_Evaluate():
    requirement = MyRequirement("MyName", "My description.")

    assert requirement.Evaluate({"result": True}) is True
    assert requirement.Evaluate({}) is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = MyRequirement("MyName", "My description.").GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 10


# ----------------------------------------------------------------------
def test_GetParametersSkip():
    parameter = MyRequirement("MyName", "My description.").GetParameters()["skip"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Skip 'MyName' requirement in the run."


# ----------------------------------------------------------------------
def test_GetParametersInclude():
    parameter = MyRequirement(
        "MyName",
        "My description.",
        requires_explicit_include=True,
    ).GetParameters()["include"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Include 'MyName' requirement in the run."


# ----------------------------------------------------------------------
def test_GetParametersIncludeIsExclusiveWithSkip():
    parameters = MyRequirement("MyName", "My description.", requires_explicit_include=True).GetParameters()

    assert list(parameters.keys()) == ["include", "value"]


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("reserved_name", "requires_explicit_include"),
    [("skip", False), ("include", True)],
)
def test_ErrorReservedParameterName(reserved_name, requires_explicit_include):
    requirement = MyRequirement(
        "MyName",
        "My description.",
        parameters={reserved_name: TyperParameter(int, 10, OptionInfo(help="Value"))},
        requires_explicit_include=requires_explicit_include,
    )

    with pytest.raises(
        ValueError,
        match=f"Parameter '{reserved_name}' is reserved by Requirement and may not be used.",
    ):
        requirement.GetParameters()


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
    parameters = MyRequirement(
        "MyName",
        "My description.",
        parameters={unreserved_name: TyperParameter(int, 10, OptionInfo(help="Value"))},
        requires_explicit_include=requires_explicit_include,
    ).GetParameters()

    assert list(parameters.keys()) == expected_keys


# ----------------------------------------------------------------------
def test_ErrorAbstract():
    with pytest.raises(TypeError):
        Requirement("MyName", "My description.")
