import enum
import inspect

import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter
from RepoAuditorWeb.web_experience_impl.form import (
    CreateGroups,
    FieldType,
    FormField,
    FormGroup,
    FormSection,
    ParseValues,
)

from conftest import MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
class MyChoice(enum.StrEnum):
    One = "one"
    Two = "two"


# ----------------------------------------------------------------------
def _CreateDynamicParameters(
    *,
    module_parameters: dict[str, TyperParameter] | None = None,
    requirement_parameters: dict[str, TyperParameter] | None = None,
) -> DynamicParameters:
    # A module contributes a 'skip' parameter of its own, so it is included when it would otherwise
    # be the only source of a parameter.
    requirements = (
        []
        if requirement_parameters is None
        else [MyRequirement("MyRequirement", "My description.", parameters=requirement_parameters)]
    )

    return DynamicParameters(
        [
            MyModule(
                "MyModule",
                "My description.",
                [MyQuery("MyQuery", requirements)],
                parameters=module_parameters,
            ),
        ],
    )


# ----------------------------------------------------------------------
def _CreateField(
    parameter: TyperParameter,
    arguments: dict[str, dict[str | None, dict[str, object]]] | None = None,
) -> FormField:
    groups = CreateGroups(
        _CreateDynamicParameters(module_parameters={"one": parameter}),
        arguments or {},
    )

    assert len(groups) == 1

    return next(field for field in groups[0].fields if field.name == "MyModule_one")


# ----------------------------------------------------------------------
def _ParseValue(parameter: TyperParameter, values: dict[str, object]) -> object:
    """Parse a submission against a single module parameter and return the value it produced."""

    arguments = ParseValues(_CreateDynamicParameters(module_parameters={"one": parameter}), values)

    return arguments["MyModule"][None]["one"]


# ----------------------------------------------------------------------
class TestFormField:
    # ----------------------------------------------------------------------
    def test_Defaults(self):
        field = FormField("MyModule_one", "one", FieldType.Text, "value")

        assert field.help == ""
        assert field.choices == []
        assert field.minimum is None
        assert field.maximum is None
        assert field.required is False

    # ----------------------------------------------------------------------
    def test_Frozen(self):
        field = FormField("MyModule_one", "one", FieldType.Text, "value")

        with pytest.raises(AttributeError):
            field.value = "other"  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestFormSection:
    # ----------------------------------------------------------------------
    def test_Defaults(self):
        section = FormSection("MyRequirement")

        assert section.fields == []
        assert section.toggle is None
        assert section.toggle_includes is False

    # ----------------------------------------------------------------------
    def test_Frozen(self):
        section = FormSection("MyRequirement")

        with pytest.raises(AttributeError):
            section.name = "Other"  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestFormGroup:
    # ----------------------------------------------------------------------
    def test_Defaults(self):
        group = FormGroup("MyModule")

        assert group.fields == []
        assert group.sections == []
        assert group.toggle is None
        assert group.toggle_includes is False

    # ----------------------------------------------------------------------
    def test_Frozen(self):
        group = FormGroup("MyModule")

        with pytest.raises(AttributeError):
            group.name = "Other"  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestCreateGroups:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        assert CreateGroups(DynamicParameters([]), {}) == []

    # ----------------------------------------------------------------------
    def test_ModuleNameIsTheGroupName(self):
        groups = CreateGroups(_CreateDynamicParameters(), {})

        assert len(groups) == 1
        assert groups[0].name == "MyModule"

    # ----------------------------------------------------------------------
    # The name of the parameter the module declared is the label; the name that identifies it
    # among all modules is not.
    def test_LabelIsTheParameterName(self):
        assert _CreateField(TyperParameter(str, "value")).label == "one"

    # ----------------------------------------------------------------------
    # The section carries the name of the requirement, so the label does not repeat it.
    def test_LabelOfARequirementIsTheParameterName(self):
        groups = CreateGroups(
            _CreateDynamicParameters(requirement_parameters={"two": TyperParameter(str, "value")}),
            {},
        )

        field = next(
            field for field in groups[0].sections[0].fields if field.name == "MyModule_MyRequirement_two"
        )

        assert field.label == "two"

    # ----------------------------------------------------------------------
    # A parameter of the module itself is displayed by the group; a parameter of a requirement is
    # displayed by a section of that requirement.
    def test_RequirementFieldsAreDisplayedInTheirOwnSection(self):
        groups = CreateGroups(
            _CreateDynamicParameters(
                module_parameters={"one": TyperParameter(str, "1")},
                requirement_parameters={"two": TyperParameter(str, "2")},
            ),
            {},
        )

        assert len(groups) == 1
        assert [field.name for field in groups[0].fields] == ["MyModule_skip", "MyModule_one"]

        assert [section.name for section in groups[0].sections] == ["MyRequirement"]
        assert [field.name for field in groups[0].sections[0].fields] == [
            "MyModule_MyRequirement_skip",
            "MyModule_MyRequirement_two",
        ]

    # ----------------------------------------------------------------------
    def test_MultipleRequirementsBecomeMultipleSections(self):
        dynamic_parameters = DynamicParameters(
            [
                MyModule(
                    "MyModule",
                    "My description.",
                    [
                        MyQuery(
                            "MyQuery",
                            [
                                MyRequirement("One", "My description."),
                                MyRequirement("Two", "My description."),
                            ],
                        ),
                    ],
                ),
            ],
        )

        groups = CreateGroups(dynamic_parameters, {})

        assert [section.name for section in groups[0].sections] == ["One", "Two"]

    # ----------------------------------------------------------------------
    def test_ModuleWithoutRequirementsHasNoSections(self):
        groups = CreateGroups(
            _CreateDynamicParameters(module_parameters={"one": TyperParameter(str, "1")}), {}
        )

        assert groups[0].sections == []

    # ----------------------------------------------------------------------
    # A requirement that runs unless it is skipped is governed by its 'skip' field.
    def test_ToggleOfASkippableRequirement(self):
        section = CreateGroups(_CreateDynamicParameters(requirement_parameters={}), {})[0].sections[0]

        assert section.toggle == "MyModule_MyRequirement_skip"
        assert section.toggle_includes is False

    # ----------------------------------------------------------------------
    # A requirement that must be asked for is governed by its 'include' field, which indicates the
    # opposite of what 'skip' indicates.
    def test_ToggleOfAnExplicitlyIncludedRequirement(self):
        dynamic_parameters = DynamicParameters(
            [
                MyModule(
                    "MyModule",
                    "My description.",
                    [
                        MyQuery(
                            "MyQuery",
                            [
                                MyRequirement(
                                    "MyRequirement",
                                    "My description.",
                                    requires_explicit_include=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        section = CreateGroups(dynamic_parameters, {})[0].sections[0]

        assert section.toggle == "MyModule_MyRequirement_include"
        assert section.toggle_includes is True

    # ----------------------------------------------------------------------
    # A module is governed by the same kind of field as the requirements it holds.
    def test_ToggleOfASkippableModule(self):
        group = CreateGroups(_CreateDynamicParameters(), {})[0]

        assert group.toggle == "MyModule_skip"
        assert group.toggle_includes is False

    # ----------------------------------------------------------------------
    def test_ToggleOfAnExplicitlyIncludedModule(self):
        dynamic_parameters = DynamicParameters(
            [MyModule("MyModule", "My description.", [], requires_explicit_include=True)],
        )

        group = CreateGroups(dynamic_parameters, {})[0]

        assert group.toggle == "MyModule_include"
        assert group.toggle_includes is True

    # ----------------------------------------------------------------------
    def test_MultipleModules(self):
        dynamic_parameters = DynamicParameters(
            [
                MyModule("One", "My description.", [], parameters={"a": TyperParameter(str, "1")}),
                MyModule("Two", "My description.", [], parameters={"b": TyperParameter(str, "2")}),
            ],
        )

        assert [group.name for group in CreateGroups(dynamic_parameters, {})] == ["One", "Two"]

    # ----------------------------------------------------------------------
    def test_DefaultIsUsedWhenNoValueIsProvided(self):
        assert _CreateField(TyperParameter(str, "default")).value == "default"

    # ----------------------------------------------------------------------
    def test_ValueOverridesTheDefault(self):
        field = _CreateField(TyperParameter(str, "default"), {"MyModule": {None: {"one": "provided"}}})

        assert field.value == "provided"

    # ----------------------------------------------------------------------
    def test_HelpAndBounds(self):
        field = _CreateField(TyperParameter(int, 10, OptionInfo(help="My help.", min=1, max=100)))

        assert field.help == "My help."
        assert field.minimum == 1
        assert field.maximum == 100

    # ----------------------------------------------------------------------
    def test_HelpAndBoundsWithoutInfo(self):
        field = _CreateField(TyperParameter(int, 10))

        assert field.help == ""
        assert field.minimum is None
        assert field.maximum is None

    # ----------------------------------------------------------------------
    # A parameter with no default cannot be satisfied by omitting it.
    def test_RequiredWhenNoDefault(self):
        assert _CreateField(TyperParameter(str)).required is True

    # ----------------------------------------------------------------------
    def test_NotRequiredWhenDefault(self):
        assert _CreateField(TyperParameter(str, "value")).required is False

    # ----------------------------------------------------------------------
    # A module that reports a missing value itself declares a default, so the help text is what
    # indicates that the value must be provided.
    def test_RequiredWhenHelpSaysSo(self):
        field = _CreateField(TyperParameter(str, None, OptionInfo(help="[REQUIRED] My help.")))

        assert field.required is True

    # ----------------------------------------------------------------------
    # The display marks the field, so repeating the prefix within the help text would be redundant.
    def test_RequiredPrefixIsRemovedFromHelp(self):
        field = _CreateField(TyperParameter(str, None, OptionInfo(help="[REQUIRED] My help.")))

        assert field.help == "My help."

    # ----------------------------------------------------------------------
    def test_RequiredPrefixWithoutOtherHelp(self):
        field = _CreateField(TyperParameter(str, "value", OptionInfo(help="[REQUIRED]")))

        assert field.required is True
        assert field.help == ""

    # ----------------------------------------------------------------------
    # The prefix indicates a required value only where the command line would display it.
    def test_RequiredPrefixElsewhereInHelpIsNotAMarker(self):
        field = _CreateField(TyperParameter(str, "value", OptionInfo(help="My help. [REQUIRED]")))

        assert field.required is False
        assert field.help == "My help. [REQUIRED]"


# ----------------------------------------------------------------------
class TestFieldTypes:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("parameter_type", "expected"),
        [
            (bool, FieldType.Boolean),
            (int, FieldType.Integer),
            (float, FieldType.Number),
            (str, FieldType.Text),
            (list[str], FieldType.List),
            (tuple[str, ...], FieldType.List),
            (MyChoice, FieldType.Choice),
        ],
    )
    def test_Types(self, parameter_type, expected):
        field = _CreateField(TyperParameter(parameter_type, None))

        assert field.type == expected

    # ----------------------------------------------------------------------
    # An optional parameter is displayed by the control of the type it may hold.
    @pytest.mark.parametrize(
        ("parameter_type", "expected"),
        [
            (str | None, FieldType.Text),
            (int | None, FieldType.Integer),
            (list[str] | None, FieldType.List),
            (MyChoice | None, FieldType.Choice),
        ],
    )
    def test_OptionalTypes(self, parameter_type, expected):
        field = _CreateField(TyperParameter(parameter_type, None))

        assert field.type == expected

    # ----------------------------------------------------------------------
    # An unsubscripted 'list' declares no origin, so it is not distinguishable from a plain value.
    def test_UnsubscriptedList(self):
        assert _CreateField(TyperParameter(list, [])).type == FieldType.Text


# ----------------------------------------------------------------------
class TestFieldValues:
    # ----------------------------------------------------------------------
    def test_ChoicesAreTheMembersOfTheEnum(self):
        field = _CreateField(TyperParameter(MyChoice, MyChoice.One))

        assert field.choices == ["one", "two"]

    # ----------------------------------------------------------------------
    # The control works with the member's value rather than the member itself.
    def test_ChoiceValueIsTheMemberValue(self):
        field = _CreateField(TyperParameter(MyChoice, MyChoice.Two))

        assert field.value == "two"

    # ----------------------------------------------------------------------
    def test_ChoiceValueThatIsNotAMember(self):
        field = _CreateField(
            TyperParameter(MyChoice, MyChoice.One),
            {"MyModule": {None: {"one": "one"}}},
        )

        assert field.value == "one"

    # ----------------------------------------------------------------------
    def test_ListValue(self):
        field = _CreateField(TyperParameter(list[str], ["a", "b"]))

        assert field.value == ["a", "b"]

    # ----------------------------------------------------------------------
    def test_TupleValueBecomesAList(self):
        field = _CreateField(TyperParameter(tuple[str, ...], ("a", "b")))

        assert field.value == ["a", "b"]

    # ----------------------------------------------------------------------
    def test_ListValueThatIsNotASequence(self):
        field = _CreateField(TyperParameter(list[str], None))

        assert field.value == []

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(("default", "expected"), [(True, True), (False, False), (None, False)])
    def test_BooleanValue(self, default, expected):
        field = _CreateField(TyperParameter(bool, default))

        assert field.value is expected

    # ----------------------------------------------------------------------
    # A control cannot display None, so an absent value is displayed as an empty control.
    @pytest.mark.parametrize("parameter_type", [str, int, float])
    def test_NoneValue(self, parameter_type):
        field = _CreateField(TyperParameter(parameter_type | None, None))

        assert field.value == ""

    # ----------------------------------------------------------------------
    def test_NumericValueIsPreserved(self):
        assert _CreateField(TyperParameter(int, 10)).value == 10


# ----------------------------------------------------------------------
class TestParseValues:
    # ----------------------------------------------------------------------
    def test_Empty(self):
        assert ParseValues(DynamicParameters([]), {}) == {}

    # ----------------------------------------------------------------------
    # The name a control submits its value under identifies the module and requirement the
    # parameter came from.
    def test_ResultIsStructured(self):
        dynamic_parameters = _CreateDynamicParameters(
            module_parameters={"one": TyperParameter(str, "1")},
            requirement_parameters={"two": TyperParameter(str, "2")},
        )

        assert ParseValues(
            dynamic_parameters,
            {"MyModule_one": "a", "MyModule_MyRequirement_two": "b"},
        ) == {
            "MyModule": {
                None: {"skip": False, "one": "a"},
                "MyRequirement": {"skip": False, "two": "b"},
            },
        }

    # ----------------------------------------------------------------------
    # A value that the form did not submit is not one the user cleared, so the default stands.
    def test_DefaultWhenNotSubmitted(self):
        assert _ParseValue(TyperParameter(str, "default"), {}) == "default"

    # ----------------------------------------------------------------------
    def test_ValuesNotDeclaredAsParametersAreIgnored(self):
        assert ParseValues(DynamicParameters([]), {"MyModule_one": "value"}) == {}

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        ("submitted", "expected"),
        [(True, True), (False, False), ("", False), (None, False)],
    )
    def test_Boolean(self, submitted, expected):
        assert _ParseValue(TyperParameter(bool, False), {"MyModule_one": submitted}) == expected

    # ----------------------------------------------------------------------
    # The form submits every value as a string, so each item is converted to the declared item type.
    def test_ListItemsAreConverted(self):
        assert _ParseValue(TyperParameter(list[int], []), {"MyModule_one": ["1", "2"]}) == [1, 2]

    # ----------------------------------------------------------------------
    # A tuple declares its item type first, so the ellipsis that follows is not mistaken for one.
    def test_TupleItemsAreConverted(self):
        assert _ParseValue(TyperParameter(tuple[int, ...], ()), {"MyModule_one": ["1", "2"]}) == [1, 2]

    # ----------------------------------------------------------------------
    def test_ListFromATuple(self):
        assert _ParseValue(TyperParameter(list[str], []), {"MyModule_one": ("a", "b")}) == ["a", "b"]

    # ----------------------------------------------------------------------
    def test_ListThatIsNotASequenceRestoresTheDefault(self):
        value = _ParseValue(TyperParameter(list[str], ["default"]), {"MyModule_one": None})

        assert value == ["default"]

    # ----------------------------------------------------------------------
    def test_Choice(self):
        assert _ParseValue(TyperParameter(MyChoice, MyChoice.One), {"MyModule_one": "two"}) == MyChoice.Two

    # ----------------------------------------------------------------------
    def test_Integer(self):
        assert _ParseValue(TyperParameter(int, 0), {"MyModule_one": "10"}) == 10

    # ----------------------------------------------------------------------
    def test_Number(self):
        assert _ParseValue(TyperParameter(float, 0.0), {"MyModule_one": "1.5"}) == 1.5

    # ----------------------------------------------------------------------
    def test_Text(self):
        assert _ParseValue(TyperParameter(str, ""), {"MyModule_one": 10}) == "10"


# ----------------------------------------------------------------------
# An empty control means the value was not provided, which modules distinguish from the empty
# string, so the empty string is never coerced to the parameter's type.
class TestParseEmptyValues:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("submitted", ["", None])
    @pytest.mark.parametrize("parameter_type", [str, int, float])
    def test_OptionalBecomesNone(self, parameter_type, submitted):
        parameter = TyperParameter(parameter_type | None, "default")

        assert _ParseValue(parameter, {"MyModule_one": submitted}) is None

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("submitted", ["", None])
    def test_DefaultIsRestored(self, submitted):
        assert _ParseValue(TyperParameter(str, "default"), {"MyModule_one": submitted}) == "default"

    # ----------------------------------------------------------------------
    # A required parameter has no default to restore, so the empty value is coerced and the module
    # reports that the value is missing.
    def test_RequiredIsCoerced(self):
        assert _ParseValue(TyperParameter(str), {"MyModule_one": ""}) == ""

    # ----------------------------------------------------------------------
    def test_RequiredIntegerRaises(self):
        parameter = TyperParameter(int)

        assert parameter.default is inspect.Parameter.empty

        with pytest.raises((TypeError, ValueError)):
            _ParseValue(parameter, {"MyModule_one": ""})
