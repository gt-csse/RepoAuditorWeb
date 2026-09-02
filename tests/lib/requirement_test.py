import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

from conftest import EvaluateValues, MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateRequirement(
    name: str = "MyName",
    parameters: dict[str, TyperParameter] | None = None,
    *,
    requires_explicit_include: bool = False,
    evaluate_values: EvaluateValues | None = None,
) -> MyRequirement:
    return MyRequirement(
        name,
        "My description.",
        parameters={"value": TyperParameter(int, 10, OptionInfo(help="Value"))}
        if parameters is None
        else parameters,
        evaluate_values=evaluate_values,
        requires_explicit_include=requires_explicit_include,
    )


# ----------------------------------------------------------------------
def _CreateModule(requirement: MyRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def test_Construct():
    requirement = _CreateRequirement()

    assert requirement.name == "MyName"
    assert requirement.description == "My description."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_RequiresExplicitInclude():
    assert _CreateRequirement(requires_explicit_include=True).requires_explicit_include is True


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = _CreateRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 10


# ----------------------------------------------------------------------
def test_GetParametersSkip():
    parameter = _CreateRequirement().GetParameters()["skip"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Skip 'MyName' requirement in the run."


# ----------------------------------------------------------------------
def test_GetParametersInclude():
    parameter = _CreateRequirement(requires_explicit_include=True).GetParameters()["include"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Include 'MyName' requirement in the run."


# ----------------------------------------------------------------------
def test_GetParametersIncludeIsExclusiveWithSkip():
    parameters = _CreateRequirement(requires_explicit_include=True).GetParameters()

    assert list(parameters.keys()) == ["include", "value"]


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("reserved_name", "requires_explicit_include"),
    [("skip", False), ("include", True)],
)
def test_ErrorReservedParameterName(reserved_name, requires_explicit_include):
    requirement = _CreateRequirement(
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
    parameters = _CreateRequirement(
        parameters={unreserved_name: TyperParameter(int, 10, OptionInfo(help="Value"))},
        requires_explicit_include=requires_explicit_include,
    ).GetParameters()

    assert list(parameters.keys()) == expected_keys


# ----------------------------------------------------------------------
def test_ErrorAbstract():
    with pytest.raises(TypeError):
        Requirement("MyName", "My description.")


# ----------------------------------------------------------------------
def test_EvaluateResultValueMembers():
    assert [value.name for value in EvaluateResultValue] == [
        "Skipped",
        "DoesNotApply",
        "Success",
        "Warning",
        "Error",
    ]


# ----------------------------------------------------------------------
def test_EvaluateResultConstruct():
    requirement = _CreateRequirement()
    module = _CreateModule(requirement)

    result = EvaluateResult(
        EvaluateResultValue.Warning,
        "My context.",
        "My resolution.",
        "My rationale.",
        requirement,
        module,
    )

    assert result.result == EvaluateResultValue.Warning
    assert result.context == "My context."
    assert result.resolution == "My resolution."
    assert result.rationale == "My rationale."
    assert result.requirement is requirement
    assert result.module is module


# ----------------------------------------------------------------------
def test_EvaluateResultFrozen():
    requirement = _CreateRequirement()

    result = EvaluateResult(
        EvaluateResultValue.Success,
        None,
        None,
        None,
        requirement,
        _CreateModule(requirement),
    )

    with pytest.raises(AttributeError):
        result.result = EvaluateResultValue.Error  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestEvaluate:
    # ----------------------------------------------------------------------
    def test_Invoked(self):
        requirement = _CreateRequirement()
        module = _CreateModule(requirement)
        query_data: dict[str, object] = {"response": {}}
        requirement_data: dict[str, object] = {"skip": False}

        result = requirement.Evaluate(module, query_data, requirement_data)

        assert result.result == EvaluateResultValue.Success
        assert result.requirement is requirement
        assert result.module is module

    # ----------------------------------------------------------------------
    def test_ForwardsDataToImpl(self):
        requirement = _CreateRequirement()
        module = _CreateModule(requirement)
        query_data: dict[str, object] = {"response": {}}
        requirement_data: dict[str, object] = {"skip": False}

        requirement.Evaluate(module, query_data, requirement_data)

        assert requirement.evaluate_args is not None
        assert requirement.evaluate_args[0] is module
        assert requirement.evaluate_args[1] is query_data
        assert requirement.evaluate_args[2] is requirement_data

    # ----------------------------------------------------------------------
    def test_ReturnsImplResult(self):
        requirement = _CreateRequirement(
            evaluate_values=EvaluateValues(EvaluateResultValue.Error, "My context."),
        )
        module = _CreateModule(requirement)

        assert requirement.Evaluate(module, {}, {"skip": False}) == EvaluateResult(
            EvaluateResultValue.Error,
            "My context.",
            None,
            None,
            requirement,
            module,
        )

    # ----------------------------------------------------------------------
    def test_Skip(self):
        requirement = _CreateRequirement()
        module = _CreateModule(requirement)

        result = requirement.Evaluate(module, {}, {"skip": True})

        assert result == EvaluateResult(
            EvaluateResultValue.Skipped,
            None,
            None,
            None,
            requirement,
            module,
        )
        assert requirement.evaluate_args is None

    # ----------------------------------------------------------------------
    def test_IncludeNotSpecified(self):
        requirement = _CreateRequirement(requires_explicit_include=True)
        module = _CreateModule(requirement)

        result = requirement.Evaluate(module, {}, {"include": False})

        assert result == EvaluateResult(
            EvaluateResultValue.Skipped,
            None,
            None,
            None,
            requirement,
            module,
        )
        assert requirement.evaluate_args is None

    # ----------------------------------------------------------------------
    def test_IncludeSpecified(self):
        requirement = _CreateRequirement(requires_explicit_include=True)

        result = requirement.Evaluate(_CreateModule(requirement), {}, {"include": True})

        assert result.result == EvaluateResultValue.Success
        assert requirement.evaluate_args is not None

    # ----------------------------------------------------------------------
    # The 'skip' parameter is only produced for requirements that do not require explicit
    # inclusion, so it is not consulted when 'include' is in play.
    def test_SkipIsIgnoredWhenIncludeIsRequired(self):
        requirement = _CreateRequirement(requires_explicit_include=True)

        assert requirement.Evaluate(
            _CreateModule(requirement), {}, {"include": True, "skip": True}
        ).result == (EvaluateResultValue.Success)

    # ----------------------------------------------------------------------
    def test_IncludeIsIgnoredWhenSkipIsRequired(self):
        requirement = _CreateRequirement()

        assert requirement.Evaluate(
            _CreateModule(requirement), {}, {"skip": False, "include": False}
        ).result == (EvaluateResultValue.Success)

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("requires_explicit_include", "missing_key"),
        [(False, "skip"), (True, "include")],
    )
    def test_ErrorMissingGatingArgument(self, requires_explicit_include, missing_key):
        requirement = _CreateRequirement(requires_explicit_include=requires_explicit_include)

        with pytest.raises(KeyError, match=missing_key):
            requirement.Evaluate(_CreateModule(requirement), {}, {})
