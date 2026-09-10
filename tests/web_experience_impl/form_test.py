import enum
import inspect

from types import UnionType

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
        assert section.description == ""
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
        assert group.description == ""
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
    def test_DescriptionsAreDisplayed(self):
        dynamic_parameters = DynamicParameters(
            [
                MyModule(
                    "MyModule",
                    "My module description.",
                    [MyQuery("MyQuery", [MyRequirement("MyRequirement", "My requirement description.")])],
                ),
            ],
        )

        groups = CreateGroups(dynamic_parameters, {})

        assert groups[0].description == "My module description."
        assert groups[0].sections[0].description == "My requirement description."

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
    # Every other type recovers None from an empty control, which a checkbox does not have, so an
    # optional bool is displayed by a control that can express the absent value.
    def test_OptionalBoolean(self):
        field = _CreateField(TyperParameter(bool | None, None))

        assert field.type == FieldType.OptionalBoolean
        assert field.choices == ["default", "yes", "no"]

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
    # A control is addressed by a single string, so the items are displayed comma-delimited.
    def test_ListValue(self):
        field = _CreateField(TyperParameter(list[str], ["a", "b"]))

        assert field.value == "a,b"

    # ----------------------------------------------------------------------
    def test_TupleValueIsDelimited(self):
        field = _CreateField(TyperParameter(tuple[str, ...], ("a", "b")))

        assert field.value == "a,b"

    # ----------------------------------------------------------------------
    def test_ListItemsThatAreNotStrings(self):
        field = _CreateField(TyperParameter(list[int], [1, 2]))

        assert field.value == "1,2"

    # ----------------------------------------------------------------------
    def test_ListValueThatIsNotASequence(self):
        field = _CreateField(TyperParameter(list[str], None))

        assert field.value == ""

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(("default", "expected"), [(True, True), (False, False), (None, False)])
    def test_BooleanValue(self, default, expected):
        field = _CreateField(TyperParameter(bool, default))

        assert field.value is expected

    # ----------------------------------------------------------------------
    # The absent value is displayed as a state of its own rather than collapsing to one of the two
    # values the parameter may hold.
    @pytest.mark.parametrize(
        ("default", "expected"),
        [(True, "yes"), (False, "no"), (None, "default")],
    )
    def test_OptionalBooleanValue(self, default, expected):
        field = _CreateField(TyperParameter(bool | None, default))

        assert field.value == expected

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
    @pytest.mark.parametrize(
        ("submitted", "expected"),
        [("yes", True), ("no", False), ("default", None), ("", None)],
    )
    def test_OptionalBoolean(self, submitted, expected):
        assert _ParseValue(TyperParameter(bool | None, None), {"MyModule_one": submitted}) is expected

    # ----------------------------------------------------------------------
    # A requirement that derives its default from other data is reached only when the submitted
    # value is None, so the state the form displays for an untouched control must parse back to it.
    @pytest.mark.parametrize("default", [None, True, False])
    def test_OptionalBooleanRoundTrip(self, default):
        parameter = TyperParameter(bool | None, default)

        displayed = _CreateField(parameter).value

        assert _ParseValue(parameter, {"MyModule_one": displayed}) is default

    # ----------------------------------------------------------------------
    # The form submits a list as a single string, so the items are split from it.
    def test_ListIsSplitOnCommas(self):
        assert _ParseValue(TyperParameter(list[str], []), {"MyModule_one": "a,b"}) == ["a", "b"]

    # ----------------------------------------------------------------------
    # Delimiting the items does not require that they be written without spaces around them.
    def test_ListItemsAreStripped(self):
        assert _ParseValue(TyperParameter(list[str], []), {"MyModule_one": " a , b "}) == ["a", "b"]

    # ----------------------------------------------------------------------
    def test_ListItemsThatAreEmptyAreDiscarded(self):
        assert _ParseValue(TyperParameter(list[str], []), {"MyModule_one": "a,,b,"}) == ["a", "b"]

    # ----------------------------------------------------------------------
    def test_SingleItemList(self):
        assert _ParseValue(TyperParameter(list[str], []), {"MyModule_one": "a"}) == ["a"]

    # ----------------------------------------------------------------------
    # The form submits every value as a string, so each item is converted to the declared item type.
    def test_ListItemsAreConverted(self):
        assert _ParseValue(TyperParameter(list[int], []), {"MyModule_one": "1,2"}) == [1, 2]

    # ----------------------------------------------------------------------
    # A tuple declares its item type first, so the ellipsis that follows is not mistaken for one.
    def test_TupleItemsAreConverted(self):
        assert _ParseValue(TyperParameter(tuple[int, ...], ()), {"MyModule_one": "1,2"}) == [1, 2]

    # ----------------------------------------------------------------------
    # A value that arrives as a sequence rather than as a string needs no splitting.
    def test_ListFromASequence(self):
        assert _ParseValue(TyperParameter(list[str], []), {"MyModule_one": ("a", "b")}) == ["a", "b"]

    # ----------------------------------------------------------------------
    def test_EmptyListRestoresTheDefault(self):
        assert _ParseValue(TyperParameter(list[str], ["default"]), {"MyModule_one": ""}) == ["default"]

    # ----------------------------------------------------------------------
    def test_EmptyListWithNoDefault(self):
        value = _ParseValue(TyperParameter(list[str], inspect.Parameter.empty), {"MyModule_one": ""})

        assert value == []

    # ----------------------------------------------------------------------
    def test_EmptyOptionalList(self):
        assert _ParseValue(TyperParameter(list[str] | None, ["default"]), {"MyModule_one": ""}) is None

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


# ----------------------------------------------------------------------
def _CreateModeDynamicParameters(
    boolean_name: str,
    *,
    requires_explicit_include: bool = False,
    extra_parameters: dict[str, TyperParameter] | None = None,
    boolean_type: type | UnionType = bool,
    boolean_default: object = False,
) -> DynamicParameters:
    """Create parameters for a requirement whose expectation is stated by a single boolean."""

    parameters = {
        boolean_name: TyperParameter(boolean_type, boolean_default, OptionInfo(help="Help.")),
    }
    parameters.update(extra_parameters or {})

    return DynamicParameters(
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
                                parameters=parameters,
                                requires_explicit_include=requires_explicit_include,
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# ----------------------------------------------------------------------
def _GetModeField(
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]] | None = None,
) -> FormField | None:
    """Return the mode field of the only requirement, or None if its parameters were not collapsed."""

    section = CreateGroups(dynamic_parameters, arguments or {})[0].sections[0]

    return next(
        (field for field in section.fields if field.type == FieldType.RequirementMode),
        None,
    )


# ----------------------------------------------------------------------
_MODE_NAME = "MyModule_MyRequirement_mode"


# ----------------------------------------------------------------------
# The parameter governing whether a requirement runs and the one stating what it expects cannot be
# set independently, so the pair is displayed as the three states that it can express.
class TestRequirementMode:
    # ----------------------------------------------------------------------
    def test_PairIsReplacedByASingleField(self):
        section = CreateGroups(_CreateModeDynamicParameters("require"), {})[0].sections[0]

        assert [(field.label, field.type) for field in section.fields] == [
            ("expectation", FieldType.RequirementMode),
        ]

    # ----------------------------------------------------------------------
    def test_ChoicesAreTheThreeStates(self):
        field = _GetModeField(_CreateModeDynamicParameters("require"))

        assert field is not None
        assert field.choices == ["skip", "require", "prohibit"]

    # ----------------------------------------------------------------------
    # The label names what the control states rather than either parameter it stands in for, since
    # neither name describes the choice and the requirement is displayed immediately above it.
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    def test_LabelNamesTheChoice(self, boolean_name):
        field = _GetModeField(_CreateModeDynamicParameters(boolean_name))

        assert field is not None
        assert field.label == "expectation"

    # ----------------------------------------------------------------------
    # The help text of neither parameter can be reused, since each describes a single state and, for
    # a 'prohibit' parameter, the one that is not selected by default. The three states are described
    # instead.
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    def test_HelpDescribesTheThreeStates(self, boolean_name):
        field = _GetModeField(_CreateModeDynamicParameters(boolean_name))

        assert field is not None
        assert field.help == (
            "Whether the requirement is skipped (skip), enforced as enabled (require), or enforced "
            "as disabled (prohibit)."
        )

    # ----------------------------------------------------------------------
    # The mode governs whether the requirement runs, so it is what the display tracks in the absence
    # of a checkbox to read.
    def test_ContainerIsGovernedByTheMode(self):
        section = CreateGroups(_CreateModeDynamicParameters("require"), {})[0].sections[0]

        assert section.toggle == _MODE_NAME
        assert section.toggle_includes is False

    # ----------------------------------------------------------------------
    # Scenario 1 is an opt-out requirement stating its expectation with 'prohibit'; scenario 2 an
    # opt-out one stating it with 'require'; scenarios 3 and 4 the opt-in counterparts of each.
    @pytest.mark.parametrize(
        ("requires_explicit_include", "boolean_name", "gate_value", "boolean_value", "expected"),
        [
            # Scenario 1
            (False, "prohibit", True, True, "skip"),
            (False, "prohibit", True, False, "skip"),
            (False, "prohibit", False, True, "prohibit"),
            (False, "prohibit", False, False, "require"),
            # Scenario 2
            (False, "require", True, True, "skip"),
            (False, "require", True, False, "skip"),
            (False, "require", False, True, "require"),
            (False, "require", False, False, "prohibit"),
            # Scenario 3
            (True, "prohibit", True, True, "prohibit"),
            (True, "prohibit", True, False, "require"),
            (True, "prohibit", False, True, "skip"),
            (True, "prohibit", False, False, "skip"),
            # Scenario 4
            (True, "require", True, True, "require"),
            (True, "require", True, False, "prohibit"),
            (True, "require", False, True, "skip"),
            (True, "require", False, False, "skip"),
        ],
    )
    def test_ValueReflectsThePair(
        self,
        requires_explicit_include,
        boolean_name,
        gate_value,
        boolean_value,
        expected,
    ):
        gate_name = "include" if requires_explicit_include else "skip"

        field = _GetModeField(
            _CreateModeDynamicParameters(
                boolean_name,
                requires_explicit_include=requires_explicit_include,
            ),
            {"MyModule": {"MyRequirement": {gate_name: gate_value, boolean_name: boolean_value}}},
        )

        assert field is not None
        assert field.value == expected

    # ----------------------------------------------------------------------
    # The submitted mode determines both of the parameters that it stands in for.
    @pytest.mark.parametrize(
        ("requires_explicit_include", "boolean_name", "mode", "expected_gate", "expected_boolean"),
        [
            # Scenario 1
            (False, "prohibit", "skip", True, True),
            (False, "prohibit", "require", False, False),
            (False, "prohibit", "prohibit", False, True),
            # Scenario 2
            (False, "require", "skip", True, False),
            (False, "require", "require", False, True),
            (False, "require", "prohibit", False, False),
            # Scenario 3
            (True, "prohibit", "skip", False, True),
            (True, "prohibit", "require", True, False),
            (True, "prohibit", "prohibit", True, True),
            # Scenario 4
            (True, "require", "skip", False, False),
            (True, "require", "require", True, True),
            (True, "require", "prohibit", True, False),
        ],
    )
    def test_SubmittedModeSetsBothParameters(
        self,
        requires_explicit_include,
        boolean_name,
        mode,
        expected_gate,
        expected_boolean,
    ):
        gate_name = "include" if requires_explicit_include else "skip"

        arguments = ParseValues(
            _CreateModeDynamicParameters(
                boolean_name,
                requires_explicit_include=requires_explicit_include,
            ),
            {_MODE_NAME: mode},
        )

        assert arguments["MyModule"]["MyRequirement"] == {
            gate_name: expected_gate,
            boolean_name: expected_boolean,
        }

    # ----------------------------------------------------------------------
    # Every state the control can hold survives being submitted and displayed again.
    @pytest.mark.parametrize("requires_explicit_include", [False, True])
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    @pytest.mark.parametrize("mode", ["skip", "require", "prohibit"])
    def test_ModeRoundTrips(self, requires_explicit_include, boolean_name, mode):
        dynamic_parameters = _CreateModeDynamicParameters(
            boolean_name,
            requires_explicit_include=requires_explicit_include,
        )

        field = _GetModeField(
            dynamic_parameters,
            ParseValues(dynamic_parameters, {_MODE_NAME: mode}),
        )

        assert field is not None
        assert field.value == mode

    # ----------------------------------------------------------------------
    # A value naming none of the modes leaves the requirement out, which is the state that asserts
    # nothing about the repository.
    @pytest.mark.parametrize("submitted", ["", None])
    def test_UnrecognizedModeSkips(self, submitted):
        arguments = ParseValues(_CreateModeDynamicParameters("require"), {_MODE_NAME: submitted})

        assert arguments["MyModule"]["MyRequirement"] == {"skip": True, "require": False}

    # ----------------------------------------------------------------------
    # A mode the form did not submit leaves the parameters at the values that they declare.
    def test_DefaultsStandWhenNotSubmitted(self):
        arguments = ParseValues(_CreateModeDynamicParameters("require"), {})

        assert arguments["MyModule"]["MyRequirement"] == {"skip": False, "require": False}


# ----------------------------------------------------------------------
# A requirement whose expectation may be absent defers to the value the module implies, which is a
# fourth choice rather than one the other three can express.
class TestOptionalRequirementMode:
    # ----------------------------------------------------------------------
    def _CreateParameters(
        self,
        boolean_name: str,
        *,
        requires_explicit_include: bool = False,
    ) -> DynamicParameters:
        return _CreateModeDynamicParameters(
            boolean_name,
            requires_explicit_include=requires_explicit_include,
            boolean_type=bool | None,
            boolean_default=None,
        )

    # ----------------------------------------------------------------------
    def test_PairIsReplacedByASingleField(self):
        section = CreateGroups(self._CreateParameters("require"), {})[0].sections[0]

        assert [(field.label, field.type) for field in section.fields] == [
            ("expectation", FieldType.RequirementMode),
        ]

    # ----------------------------------------------------------------------
    # The absent value is offered alongside the three states a plain boolean can express, and sits
    # beside the states it resolves to.
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    def test_ChoicesIncludeTheDefault(self, boolean_name):
        field = _GetModeField(self._CreateParameters(boolean_name))

        assert field is not None
        assert field.choices == ["skip", "use default", "require", "prohibit"]

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    def test_HelpDescribesTheFourStates(self, boolean_name):
        field = _GetModeField(self._CreateParameters(boolean_name))

        assert field is not None
        assert field.help == (
            "Whether the requirement is skipped (skip), left to the value the module implies (use "
            "default), enforced as enabled (require), or enforced as disabled (prohibit)."
        )

    # ----------------------------------------------------------------------
    # A parameter that is absent by default starts the control on the choice that leaves it absent.
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    def test_DefaultValueIsTheDefaultChoice(self, boolean_name):
        field = _GetModeField(self._CreateParameters(boolean_name))

        assert field is not None
        assert field.value == "use default"

    # ----------------------------------------------------------------------
    # The absent value reads as 'use default' whichever name the boolean carries, since the negation
    # a 'prohibit' parameter applies does not apply to the absence of a value.
    @pytest.mark.parametrize(
        ("requires_explicit_include", "boolean_name", "gate_value", "boolean_value", "expected"),
        [
            # An opt-out requirement stating its expectation with 'prohibit'.
            (False, "prohibit", True, None, "skip"),
            (False, "prohibit", True, True, "skip"),
            (False, "prohibit", True, False, "skip"),
            (False, "prohibit", False, None, "use default"),
            (False, "prohibit", False, True, "prohibit"),
            (False, "prohibit", False, False, "require"),
            # An opt-out requirement stating its expectation with 'require'.
            (False, "require", True, None, "skip"),
            (False, "require", True, True, "skip"),
            (False, "require", True, False, "skip"),
            (False, "require", False, None, "use default"),
            (False, "require", False, True, "require"),
            (False, "require", False, False, "prohibit"),
            # An opt-in requirement stating its expectation with 'prohibit'.
            (True, "prohibit", False, None, "skip"),
            (True, "prohibit", False, True, "skip"),
            (True, "prohibit", False, False, "skip"),
            (True, "prohibit", True, None, "use default"),
            (True, "prohibit", True, True, "prohibit"),
            (True, "prohibit", True, False, "require"),
            # An opt-in requirement stating its expectation with 'require'.
            (True, "require", False, None, "skip"),
            (True, "require", False, True, "skip"),
            (True, "require", False, False, "skip"),
            (True, "require", True, None, "use default"),
            (True, "require", True, True, "require"),
            (True, "require", True, False, "prohibit"),
        ],
    )
    def test_ValueReflectsThePair(
        self,
        requires_explicit_include,
        boolean_name,
        gate_value,
        boolean_value,
        expected,
    ):
        gate_name = "include" if requires_explicit_include else "skip"

        field = _GetModeField(
            self._CreateParameters(
                boolean_name,
                requires_explicit_include=requires_explicit_include,
            ),
            {"MyModule": {"MyRequirement": {gate_name: gate_value, boolean_name: boolean_value}}},
        )

        assert field is not None
        assert field.value == expected

    # ----------------------------------------------------------------------
    # A requirement that states no expectation leaves the boolean absent, whether because it is
    # skipped or because the value the module implies was accepted.
    @pytest.mark.parametrize(
        ("requires_explicit_include", "boolean_name", "mode", "expected_gate", "expected_boolean"),
        [
            # An opt-out requirement stating its expectation with 'prohibit'.
            (False, "prohibit", "skip", True, None),
            (False, "prohibit", "use default", False, None),
            (False, "prohibit", "require", False, False),
            (False, "prohibit", "prohibit", False, True),
            # An opt-out requirement stating its expectation with 'require'.
            (False, "require", "skip", True, None),
            (False, "require", "use default", False, None),
            (False, "require", "require", False, True),
            (False, "require", "prohibit", False, False),
            # An opt-in requirement stating its expectation with 'prohibit'.
            (True, "prohibit", "skip", False, None),
            (True, "prohibit", "use default", True, None),
            (True, "prohibit", "require", True, False),
            (True, "prohibit", "prohibit", True, True),
            # An opt-in requirement stating its expectation with 'require'.
            (True, "require", "skip", False, None),
            (True, "require", "use default", True, None),
            (True, "require", "require", True, True),
            (True, "require", "prohibit", True, False),
        ],
    )
    def test_SubmittedModeSetsBothParameters(
        self,
        requires_explicit_include,
        boolean_name,
        mode,
        expected_gate,
        expected_boolean,
    ):
        gate_name = "include" if requires_explicit_include else "skip"

        arguments = ParseValues(
            self._CreateParameters(
                boolean_name,
                requires_explicit_include=requires_explicit_include,
            ),
            {_MODE_NAME: mode},
        )

        assert arguments["MyModule"]["MyRequirement"] == {
            gate_name: expected_gate,
            boolean_name: expected_boolean,
        }

    # ----------------------------------------------------------------------
    # Every state the control can hold survives being submitted and displayed again.
    @pytest.mark.parametrize("requires_explicit_include", [False, True])
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    @pytest.mark.parametrize("mode", ["skip", "use default", "require", "prohibit"])
    def test_ModeRoundTrips(self, requires_explicit_include, boolean_name, mode):
        dynamic_parameters = self._CreateParameters(
            boolean_name,
            requires_explicit_include=requires_explicit_include,
        )

        field = _GetModeField(
            dynamic_parameters,
            ParseValues(dynamic_parameters, {_MODE_NAME: mode}),
        )

        assert field is not None
        assert field.value == mode

    # ----------------------------------------------------------------------
    # Skipping states no expectation, so re-including the requirement offers the value the module
    # implies rather than one the user never chose.
    @pytest.mark.parametrize("boolean_name", ["require", "prohibit"])
    def test_SkipLeavesNoExpectation(self, boolean_name):
        dynamic_parameters = self._CreateParameters(boolean_name)

        arguments = ParseValues(dynamic_parameters, {_MODE_NAME: "skip"})

        assert arguments["MyModule"]["MyRequirement"][boolean_name] is None


# ----------------------------------------------------------------------
# A requirement stating more than whether it runs and what it expects cannot be reduced to the
# modes, so it keeps the controls that can express what it states.
class TestRequirementModeExclusions:
    # ----------------------------------------------------------------------
    def test_AdditionalParameterIsNotCollapsed(self):
        dynamic_parameters = _CreateModeDynamicParameters(
            "prohibit",
            extra_parameters={"value": TyperParameter(int, 1, OptionInfo(help="Help."))},
        )

        assert _GetModeField(dynamic_parameters) is None

        section = CreateGroups(dynamic_parameters, {})[0].sections[0]

        assert section.toggle == "MyModule_MyRequirement_skip"
        assert [(field.label, field.type) for field in section.fields] == [
            ("skip", FieldType.Boolean),
            ("prohibit", FieldType.Boolean),
            ("value", FieldType.Integer),
        ]

    # ----------------------------------------------------------------------
    # A requirement stating nothing beyond whether it runs has no expectation to fold in.
    def test_ToggleOnlyRequirementIsNotCollapsed(self):
        section = CreateGroups(_CreateDynamicParameters(requirement_parameters={}), {})[0].sections[0]

        assert [(field.label, field.type) for field in section.fields] == [
            ("skip", FieldType.Boolean),
        ]
        assert section.toggle == "MyModule_MyRequirement_skip"

    # ----------------------------------------------------------------------
    # A boolean stating something other than the requirement's expectation is not one that the three
    # modes describe.
    def test_UnrelatedBooleanIsNotCollapsed(self):
        assert _GetModeField(_CreateModeDynamicParameters("other")) is None

    # ----------------------------------------------------------------------
    # A module is not a requirement, so its own parameters are never folded together.
    def test_ModuleParametersAreNotCollapsed(self):
        group = CreateGroups(
            _CreateDynamicParameters(
                module_parameters={"require": TyperParameter(bool, False, OptionInfo(help="Help."))},
            ),
            {},
        )[0]

        assert group.toggle == "MyModule_skip"
        assert [(field.label, field.type) for field in group.fields] == [
            ("skip", FieldType.Boolean),
            ("require", FieldType.Boolean),
        ]
