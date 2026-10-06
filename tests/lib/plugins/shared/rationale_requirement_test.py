from typing import override

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
class MyRationaleRequirement(RationaleRequirement):
    def __init__(self, *args, resolution: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.resolution = resolution

    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        *,
        evaluate_all: bool,
    ) -> EvaluateResult:
        if self.resolution is None:
            return self._CreateResult(module, requirement_data, EvaluateResultValue.Success, "My context.")

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Error,
            "My context.",
            self.resolution,
        )


# ----------------------------------------------------------------------
class MyParameterizedRationaleRequirement(MyRationaleRequirement):
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {"value": TyperParameter(int, 10, OptionInfo(help="Value"))}


# ----------------------------------------------------------------------
def _Evaluate(requirement: MyRationaleRequirement, requirement_data: dict[str, object]) -> EvaluateResult:
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])

    return requirement.Evaluate(module, {}, requirement_data)


# ----------------------------------------------------------------------
def test_Construct():
    requirement = MyRationaleRequirement("MyName", "My description.", "My rationale.")

    assert requirement.name == "MyName"
    assert requirement.description == "My description."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_ConstructRequiresExplicitInclude():
    requirement = MyRationaleRequirement(
        "MyName",
        "My description.",
        "My rationale.",
        requires_explicit_include=True,
    )

    assert requirement.requires_explicit_include is True
    assert list(requirement.GetParameters().keys()) == ["include"]


# ----------------------------------------------------------------------
def test_GetParameters():
    requirement = MyRationaleRequirement("MyName", "My description.", "My rationale.")

    assert list(requirement.GetParameters().keys()) == ["skip"]


# ----------------------------------------------------------------------
def test_Evaluate():
    requirement = MyRationaleRequirement("MyName", "My description.", "My rationale.")

    result = _Evaluate(requirement, {"skip": False})

    assert result.result == EvaluateResultValue.Success
    assert result.context == "My context."
    assert result.resolution is None
    assert result.rationale == "My rationale."
    assert result.requirement is requirement
    assert result.module.name == "MyModule"


# ----------------------------------------------------------------------
def test_EvaluateWithResolution():
    requirement = MyRationaleRequirement(
        "MyName",
        "My description.",
        "My rationale.",
        resolution="My resolution.",
    )

    result = _Evaluate(requirement, {"skip": False})

    assert result.result == EvaluateResultValue.Error
    assert result.resolution == "My resolution."
    assert result.rationale == "My rationale."


# ----------------------------------------------------------------------
def test_EvaluateDefaultValues():
    requirement = MyParameterizedRationaleRequirement("MyName", "My description.", "My rationale.")

    assert _Evaluate(requirement, {"skip": False, "value": 10}).rationale == "My rationale."


# ----------------------------------------------------------------------
def test_EvaluateOverriddenValues():
    requirement = MyParameterizedRationaleRequirement("MyName", "My description.", "My rationale.")

    assert _Evaluate(requirement, {"skip": False, "value": 20}).rationale is None
