import inspect
import re

from typing import override

import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.query import Query
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

        self.parameters = {} if parameters is None else parameters

    @override
    def Evaluate(self, query_results: dict) -> bool:
        return True

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return self.parameters


# ----------------------------------------------------------------------
class MyModule(Module):
    def __init__(
        self,
        *args,
        parameters: dict[str, TyperParameter] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.parameters = {} if parameters is None else parameters

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return self.parameters


# ----------------------------------------------------------------------
def _CreateModule(
    name: str = "MyModule",
    parameters: dict[str, TyperParameter] | None = None,
    requirements: list[Requirement] | None = None,
) -> MyModule:
    return MyModule(
        name,
        "My description.",
        [Query("MyQuery", requirements or [])],
        parameters=parameters,
    )


# ----------------------------------------------------------------------
class TestTyperParameter:
    # ----------------------------------------------------------------------
    def test_Defaults(self):
        param = TyperParameter(int)

        assert param.type is int
        assert param.default is inspect.Parameter.empty
        assert param.info is None

    # ----------------------------------------------------------------------
    def test_AllValues(self):
        info = OptionInfo(help="Help text")
        param = TyperParameter(str, "value", info)

        assert param.type is str
        assert param.default == "value"
        assert param.info is info

    # ----------------------------------------------------------------------
    def test_Frozen(self):
        param = TyperParameter(int, 10)

        with pytest.raises(AttributeError):
            param.default = 20  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestDynamicParameters:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        assert DynamicParameters([]).dynamic_parameters == {}

    # ----------------------------------------------------------------------
    def test_ModuleParameters(self):
        parameter = TyperParameter(int, 10, OptionInfo(help="One"))
        parameters = DynamicParameters([_CreateModule(parameters={"one": parameter})]).dynamic_parameters

        assert list(parameters.keys()) == ["MyModule_skip", "MyModule_one"]
        assert parameters["MyModule_one"] is parameter

    # ----------------------------------------------------------------------
    def test_RequirementParameters(self):
        parameter = TyperParameter(str, "value", OptionInfo(help="Two"))

        parameters = DynamicParameters(
            [
                _CreateModule(
                    requirements=[
                        MyRequirement(
                            "MyRequirement",
                            "My requirement description.",
                            parameters={"two": parameter},
                        ),
                    ],
                ),
            ],
        ).dynamic_parameters

        assert list(parameters.keys()) == [
            "MyModule_skip",
            "MyModule_MyRequirement_skip",
            "MyModule_MyRequirement_two",
        ]
        assert parameters["MyModule_MyRequirement_two"] is parameter

    # ----------------------------------------------------------------------
    def test_MultipleModules(self):
        parameters = DynamicParameters(
            [
                _CreateModule("One", {"a": TyperParameter(int, 1, OptionInfo())}),
                _CreateModule("Two", {"b": TyperParameter(int, 2, OptionInfo())}),
            ],
        ).dynamic_parameters

        assert list(parameters.keys()) == ["One_skip", "One_a", "Two_skip", "Two_b"]

    # ----------------------------------------------------------------------
    def test_ParameterNamesMayContainUnderscores(self):
        parameters = DynamicParameters(
            [_CreateModule(parameters={"one_two_three": TyperParameter(int, 1, OptionInfo())})],
        ).dynamic_parameters

        assert "MyModule_one_two_three" in parameters

    # ----------------------------------------------------------------------
    # Names become part of a python function signature, so anything that is not an identifier is
    # rejected regardless of the specific character used.
    # Keywords are valid identifiers but cannot be used as parameter names in a function signature.
    _invalid_identifiers = ["My<Name", "My Name", "My-Name", "My.Name", "1Name", "", "class", "None"]

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("name", _invalid_identifiers)
    def test_ErrorInvalidModuleName(self, name):
        with pytest.raises(
            ValueError,
            match=f"'{re.escape(name)}' is not a valid identifier.",
        ):
            DynamicParameters([_CreateModule(name)])

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("name", _invalid_identifiers)
    def test_ErrorInvalidParameterName(self, name):
        module = _CreateModule(parameters={name: TyperParameter(int, 1, OptionInfo())})

        with pytest.raises(
            ValueError,
            match=f"'{re.escape(name)}' is not a valid identifier.",
        ):
            DynamicParameters([module])

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("name", _invalid_identifiers)
    def test_ErrorInvalidRequirementName(self, name):
        module = _CreateModule(
            requirements=[MyRequirement(name, "My requirement description.")],
        )

        with pytest.raises(
            ValueError,
            match=f"'{re.escape(name)}' is not a valid identifier.",
        ):
            DynamicParameters([module])

    # ----------------------------------------------------------------------
    # Underscores delimit the module, requirement, and parameter portions of a generated name, so
    # only the parameter portion may contain them.
    def test_ErrorUnderscoreInModuleName(self):
        with pytest.raises(
            ValueError,
            match="'My_Module' contains '_', which is not allowed.",
        ):
            DynamicParameters([_CreateModule("My_Module")])

    # ----------------------------------------------------------------------
    def test_ErrorUnderscoreInRequirementName(self):
        module = _CreateModule(
            requirements=[MyRequirement("My_Requirement", "My requirement description.")],
        )

        with pytest.raises(
            ValueError,
            match="'My_Requirement' contains '_', which is not allowed.",
        ):
            DynamicParameters([module])

    # ----------------------------------------------------------------------
    def test_ErrorDuplicateModuleParameter(self):
        parameter = TyperParameter(int, 1, OptionInfo())

        with pytest.raises(
            ValueError,
            match="The parameter name 'MyModule_one' is used by multiple modules.",
        ):
            DynamicParameters(
                [
                    MyModule(
                        "MyModule",
                        "My description.",
                        [Query("MyQuery", [])],
                        parameters={"one": parameter},
                    ),
                    # The same module name produces the same prefix, so the parameter collides. A
                    # differing base parameter ('include' vs. 'skip') is needed to reach the
                    # derived parameter comparison.
                    MyModule(
                        "MyModule",
                        "My description.",
                        [Query("MyQuery", [])],
                        parameters={"one": parameter},
                        requires_explicit_include=True,
                    ),
                ],
            )

    # ----------------------------------------------------------------------
    def test_ErrorDuplicateModuleBaseParameter(self):
        with pytest.raises(
            ValueError,
            match="The parameter name 'MyModule_skip' is used by multiple modules.",
        ):
            DynamicParameters([_CreateModule(), _CreateModule()])

    # ----------------------------------------------------------------------
    def test_ErrorDuplicateRequirementParameter(self):
        parameter = TyperParameter(str, "2", OptionInfo())

        with pytest.raises(
            ValueError,
            match="The parameter name 'MyModule_MyRequirement_two' is used by multiple requirements.",
        ):
            DynamicParameters(
                [
                    MyModule(
                        "MyModule",
                        "My description.",
                        [
                            Query(
                                "MyQuery",
                                [
                                    MyRequirement(
                                        "MyRequirement",
                                        "My requirement description.",
                                        parameters={"two": parameter},
                                    ),
                                ],
                            ),
                        ],
                    ),
                    MyModule(
                        "MyModule",
                        "My description.",
                        [
                            Query(
                                "MyQuery",
                                [
                                    MyRequirement(
                                        "MyRequirement",
                                        "My requirement description.",
                                        parameters={"two": parameter},
                                        requires_explicit_include=True,
                                    ),
                                ],
                            ),
                        ],
                        requires_explicit_include=True,
                    ),
                ],
            )


# ----------------------------------------------------------------------
class TestParse:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        assert DynamicParameters([]).Parse({}) == {}

    # ----------------------------------------------------------------------
    def test_ModuleParameter(self):
        dynamic_parameters = DynamicParameters(
            [_CreateModule(parameters={"one": TyperParameter(int, 1, OptionInfo())})],
        )

        assert dynamic_parameters.Parse({"MyModule_one": 100}) == {"MyModule": {None: {"one": 100}}}

    # ----------------------------------------------------------------------
    def test_RequirementParameter(self):
        dynamic_parameters = DynamicParameters(
            [
                _CreateModule(
                    requirements=[
                        MyRequirement(
                            "MyRequirement",
                            "My requirement description.",
                            parameters={"two": TyperParameter(str, "2", OptionInfo())},
                        ),
                    ],
                ),
            ],
        )

        assert dynamic_parameters.Parse({"MyModule_MyRequirement_two": "value"}) == {
            "MyModule": {"MyRequirement": {"two": "value"}},
        }

    # ----------------------------------------------------------------------
    def test_ModuleAndRequirementParameters(self):
        dynamic_parameters = DynamicParameters(
            [
                _CreateModule(
                    parameters={"one": TyperParameter(int, 1, OptionInfo())},
                    requirements=[
                        MyRequirement(
                            "MyRequirement",
                            "My requirement description.",
                            parameters={"two": TyperParameter(str, "2", OptionInfo())},
                        ),
                    ],
                ),
            ],
        )

        assert dynamic_parameters.Parse(
            {
                "MyModule_one": 100,
                "MyModule_MyRequirement_two": "value",
            },
        ) == {
            "MyModule": {
                None: {"one": 100},
                "MyRequirement": {"two": "value"},
            },
        }

    # ----------------------------------------------------------------------
    def test_RequirementNameResemblingModuleParameter(self):
        # A requirement parameter's name is indistinguishable from a module parameter containing
        # underscores, so the argument must resolve to the requirement that declared it.
        dynamic_parameters = DynamicParameters(
            [
                _CreateModule(
                    parameters={"MyRequirement_two": TyperParameter(int, 1, OptionInfo())},
                    requirements=[
                        MyRequirement(
                            "MyOtherRequirement",
                            "My requirement description.",
                            parameters={"two": TyperParameter(str, "2", OptionInfo())},
                        ),
                    ],
                ),
            ],
        )

        assert dynamic_parameters.Parse(
            {
                "MyModule_MyRequirement_two": 100,
                "MyModule_MyOtherRequirement_two": "value",
            },
        ) == {
            "MyModule": {
                None: {"MyRequirement_two": 100},
                "MyOtherRequirement": {"two": "value"},
            },
        }

    # ----------------------------------------------------------------------
    def test_MultipleModules(self):
        dynamic_parameters = DynamicParameters(
            [
                _CreateModule("One", {"a": TyperParameter(int, 1, OptionInfo())}),
                _CreateModule("Two", {"b": TyperParameter(int, 2, OptionInfo())}),
            ],
        )

        assert dynamic_parameters.Parse({"One_a": 10, "Two_b": 20}) == {
            "One": {None: {"a": 10}},
            "Two": {None: {"b": 20}},
        }

    # ----------------------------------------------------------------------
    def test_ParameterNamesWithUnderscores(self):
        dynamic_parameters = DynamicParameters(
            [_CreateModule(parameters={"one_two_three": TyperParameter(int, 1, OptionInfo())})],
        )

        assert dynamic_parameters.Parse({"MyModule_one_two_three": 100}) == {
            "MyModule": {None: {"one_two_three": 100}},
        }

    # ----------------------------------------------------------------------
    def test_ErrorUndeclaredParameterOnKnownModule(self):
        dynamic_parameters = DynamicParameters(
            [_CreateModule(parameters={"one": TyperParameter(int, 1, OptionInfo())})],
        )

        with pytest.raises(
            ValueError,
            match="'MyModule_extra' does not correspond to a valid parameter.",
        ):
            dynamic_parameters.Parse({"MyModule_extra": "value"})

    # ----------------------------------------------------------------------
    def test_ErrorUnknownModule(self):
        dynamic_parameters = DynamicParameters(
            [_CreateModule(parameters={"one": TyperParameter(int, 1, OptionInfo())})],
        )

        with pytest.raises(ValueError, match="does not correspond to a valid parameter."):
            dynamic_parameters.Parse({"Other_one": 100})

    # ----------------------------------------------------------------------
    def test_ErrorUnprefixedArgument(self):
        with pytest.raises(ValueError, match="does not correspond to a valid parameter."):
            DynamicParameters([]).Parse({"port": 1234})
