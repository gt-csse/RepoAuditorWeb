import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
class MyOtherRequirement(MyRequirement):
    """Distinct class name, so duplicate-name errors assert which class landed in which slot."""


# ----------------------------------------------------------------------
def _CreateModule(
    queries: list[MyQuery] | None = None,
    parameters: dict[str, TyperParameter] | None = None,
    *,
    requires_explicit_include: bool = False,
    module_data: dict[str | None, dict[str, object]] | None = None,
) -> MyModule:
    return MyModule(
        "MyName",
        "My description.",
        [] if queries is None else queries,
        parameters={"value": TyperParameter(int, 10, OptionInfo(help="Value"))}
        if parameters is None
        else parameters,
        module_data=module_data,
        requires_explicit_include=requires_explicit_include,
    )


# ----------------------------------------------------------------------
def test_Construct():
    module = _CreateModule()

    assert module.name == "MyName"
    assert module.description == "My description."
    assert module.queries == []
    assert module.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_Queries():
    queries = [MyQuery("MyQuery", [MyRequirement("MyRequirement", "My requirement description.")])]

    assert _CreateModule(queries).queries is queries


# ----------------------------------------------------------------------
def test_RequiresExplicitInclude():
    assert _CreateModule(requires_explicit_include=True).requires_explicit_include is True


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = _CreateModule().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 10


# ----------------------------------------------------------------------
def test_GetParametersSkip():
    parameter = _CreateModule().GetParameters()["skip"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Skip 'MyName' module in the run."


# ----------------------------------------------------------------------
def test_GetParametersInclude():
    parameter = _CreateModule(requires_explicit_include=True).GetParameters()["include"]

    assert parameter.type is bool
    assert parameter.default is False
    assert parameter.info is not None
    assert parameter.info.help == "Include 'MyName' module in the run."


# ----------------------------------------------------------------------
def test_GetParametersIncludeIsExclusiveWithSkip():
    parameters = _CreateModule(requires_explicit_include=True).GetParameters()

    assert list(parameters.keys()) == ["include", "value"]


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("reserved_name", "requires_explicit_include"),
    [("skip", False), ("include", True)],
)
def test_ErrorReservedParameterName(reserved_name, requires_explicit_include):
    module = _CreateModule(
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
    parameters = _CreateModule(
        parameters={unreserved_name: TyperParameter(int, 10, OptionInfo(help="Value"))},
        requires_explicit_include=requires_explicit_include,
    ).GetParameters()

    assert list(parameters.keys()) == expected_keys


# ----------------------------------------------------------------------
def test_UniqueRequirementNamesAcrossQueries():
    queries = [
        MyQuery("Query1", [MyRequirement("Requirement1", "Description 1.")]),
        MyQuery("Query2", [MyRequirement("Requirement2", "Description 2.")]),
    ]

    assert _CreateModule(queries).queries is queries


# ----------------------------------------------------------------------
def test_ErrorDuplicateRequirementNameInSameQuery():
    queries = [
        MyQuery(
            "MyQuery",
            [
                MyRequirement("MyRequirement", "Description 1."),
                MyOtherRequirement("MyRequirement", "Description 2."),
            ],
        ),
    ]

    with pytest.raises(ValueError) as exc_info:
        _CreateModule(queries)

    assert str(exc_info.value) == (
        "The requirement name 'MyRequirement' is used in both 'MyRequirement' and 'MyOtherRequirement'."
        " Requirement names must be unique across all queries in a module."
    )


# ----------------------------------------------------------------------
def test_ErrorDuplicateRequirementNameAcrossQueries():
    queries = [
        MyQuery("Query1", [MyRequirement("MyRequirement", "Description 1.")]),
        MyQuery("Query2", [MyOtherRequirement("MyRequirement", "Description 2.")]),
    ]

    with pytest.raises(ValueError) as exc_info:
        _CreateModule(queries)

    assert str(exc_info.value) == (
        "The requirement name 'MyRequirement' is used in both 'MyRequirement' and 'MyOtherRequirement'."
        " Requirement names must be unique across all queries in a module."
    )


# ----------------------------------------------------------------------
def test_ErrorAbstract():
    with pytest.raises(TypeError):
        Module("MyName", "My description.", [])


# ----------------------------------------------------------------------
class TestGetModuleData:
    # ----------------------------------------------------------------------
    def test_Invoked(self):
        expected: dict[str | None, dict[str, object]] = {None: {"session": "value"}}
        module = _CreateModule(module_data=expected)

        assert module.GetModuleData({None: {"skip": False}}) is expected

    # ----------------------------------------------------------------------
    def test_ForwardsArgumentsToImpl(self):
        module = _CreateModule()
        arguments: dict[str | None, dict[str, object]] = {None: {"skip": False}, "MyRequirement": {}}

        assert module.GetModuleData(arguments) is arguments
        assert module.module_data_args is arguments

    # ----------------------------------------------------------------------
    def test_Skip(self):
        module = _CreateModule()

        assert module.GetModuleData({None: {"skip": True}}) is None
        assert module.module_data_args is None

    # ----------------------------------------------------------------------
    def test_IncludeNotSpecified(self):
        module = _CreateModule(requires_explicit_include=True)

        assert module.GetModuleData({None: {"include": False}}) is None
        assert module.module_data_args is None

    # ----------------------------------------------------------------------
    def test_IncludeSpecified(self):
        module = _CreateModule(requires_explicit_include=True)
        arguments: dict[str | None, dict[str, object]] = {None: {"include": True}}

        assert module.GetModuleData(arguments) is arguments

    # ----------------------------------------------------------------------
    # The 'skip' parameter is only produced for modules that do not require explicit inclusion, so
    # it is not consulted when 'include' is in play.
    def test_SkipIsIgnoredWhenIncludeIsRequired(self):
        module = _CreateModule(requires_explicit_include=True)

        assert module.GetModuleData({None: {"include": True, "skip": True}}) is not None

    # ----------------------------------------------------------------------
    def test_IncludeIsIgnoredWhenSkipIsRequired(self):
        module = _CreateModule()

        assert module.GetModuleData({None: {"skip": False, "include": False}}) is not None

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("requires_explicit_include", "missing_key"),
        [(False, "skip"), (True, "include")],
    )
    def test_ErrorMissingGatingArgument(self, requires_explicit_include, missing_key):
        module = _CreateModule(requires_explicit_include=requires_explicit_include)

        with pytest.raises(KeyError, match=missing_key):
            module.GetModuleData({None: {}})

    # ----------------------------------------------------------------------
    def test_ErrorMissingModuleArguments(self):
        with pytest.raises(KeyError):
            _CreateModule().GetModuleData({})
