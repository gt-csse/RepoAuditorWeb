"""Translates dynamic parameters into form fields and form values back into arguments."""

import enum
import inspect

from dataclasses import dataclass, field
from types import UnionType
from typing import get_args, get_origin, TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.dynamic_parameters import ArgumentInfo, DynamicParameters, TyperParameter


# ----------------------------------------------------------------------
class FieldType(enum.StrEnum):
    """The control used to display a field."""

    Boolean = "boolean"
    # A checkbox has no empty state, so a bool that may also be None needs a control that can
    # express the absent value alongside the two it may hold.
    OptionalBoolean = "optional_boolean"
    Integer = "integer"
    Number = "number"
    Text = "text"
    Choice = "choice"
    List = "list"
    # Whether a requirement runs and what it then expects are two parameters that cannot be set
    # independently: the expectation is meaningless while the requirement is skipped. Presenting
    # them as one control makes the three states that the pair can express the thing being chosen.
    RequirementMode = "requirement_mode"


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class FormField:
    """A single dynamic parameter as displayed within the form."""

    name: str
    label: str
    type: FieldType
    value: object
    help: str = ""
    choices: list[str] = field(default_factory=list)
    minimum: float | None = None
    maximum: float | None = None
    required: bool = False


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class FormContainer:
    """Fields displayed under a name, along with the field that governs whether they are run."""

    name: str
    fields: list[FormField] = field(default_factory=list)
    description: str = ""

    # Modules and requirements alike are governed by a single field, which the display indicates
    # alongside the name so that it is apparent without expanding the container. One that must be
    # asked for names that field 'include'; one that runs by default names it 'skip'.
    toggle: str | None = None
    toggle_includes: bool = False


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class FormSection(FormContainer):
    """The fields of a single requirement within a module."""


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class FormGroup(FormContainer):
    """The fields of a module, followed by a section for each of its requirements."""

    sections: list[FormSection] = field(default_factory=list)


# ----------------------------------------------------------------------
def CreateGroups(
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
) -> list[FormGroup]:
    """Create the form's display groups from the dynamic parameters and their current values."""

    # A requirement name of None indicates a parameter of the module itself, which is displayed
    # ahead of the requirements rather than in a section of its own.
    groups: dict[str, dict[str | None, list[FormField]]] = {}

    mode_lookup = _CreateModeLookup(dynamic_parameters)

    for name, parameter in dynamic_parameters.dynamic_parameters.items():
        argument_info = dynamic_parameters.argument_lookup[name]

        value = (
            arguments.get(argument_info.module_name, {})
            .get(argument_info.requirement_name, {})
            .get(argument_info.parameter_name, parameter.default)
        )

        fields = groups.setdefault(argument_info.module_name, {}).setdefault(
            argument_info.requirement_name,
            [],
        )

        mode_parameters = mode_lookup.get((argument_info.module_name, argument_info.requirement_name))

        if mode_parameters is not None:
            # The pair is displayed as one control, which is created once rather than by each of the
            # parameters it stands in for. The toggle is what creates it, so that the mode occupies
            # the position the toggle would have and the requirement's fields keep their order.
            if name == mode_parameters.toggle_name:
                fields.append(
                    _CreateModeField(
                        dynamic_parameters,
                        arguments,
                        argument_info,
                        mode_parameters,
                        toggle_value=value,
                    ),
                )

            continue

        # A control is addressed by a single string, so the name that identifies the parameter
        # among all modules is what the page submits its value under.
        fields.append(_CreateField(name, argument_info.parameter_name, parameter, value))

    descriptions = dynamic_parameters.description_lookup

    return [
        _CreateContainer(
            FormGroup,
            name,
            fields.get(None, []),
            descriptions[name][None],
            sections=[
                _CreateContainer(
                    FormSection,
                    requirement_name,
                    requirement_fields,
                    descriptions[name][requirement_name],
                )
                for requirement_name, requirement_fields in fields.items()
                if requirement_name is not None
            ],
        )
        for name, fields in groups.items()
    ]


# ----------------------------------------------------------------------
def ParseValues(
    dynamic_parameters: DynamicParameters,
    values: dict[str, object],
) -> dict[str, dict[str | None, dict[str, object]]]:
    """Convert values submitted by the form into structured arguments of the declared types."""

    results: dict[str, dict[str | None, dict[str, object]]] = {}

    # One mode control stands in for two parameters, so what it submitted is resolved into a value
    # for each of them before the parameters are visited.
    mode_values: dict[str, bool | None] = {}

    for (module_name, requirement_name), mode_parameters in _CreateModeLookup(dynamic_parameters).items():
        mode_name = f"{module_name}_{requirement_name}_{_MODE_PARAMETER_NAME}"

        if mode_name in values:
            mode_values.update(_CreateModeValues(mode_parameters, values[mode_name]))

    for name, parameter in dynamic_parameters.dynamic_parameters.items():
        argument_info = dynamic_parameters.argument_lookup[name]

        if name in mode_values:
            value: object = mode_values[name]
        elif name in values:
            value = _CoerceValue(parameter, values[name])
        else:
            value = parameter.default

        results.setdefault(argument_info.module_name, {}).setdefault(
            argument_info.requirement_name,
            {},
        )[argument_info.parameter_name] = value

    return results


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_INCLUDE_PARAMETER_NAME = "include"
_SKIP_PARAMETER_NAME = "skip"

# The two names a requirement may give the boolean that states what it expects. One names the
# affirmative directly; the other names its negation, which is how a requirement whose default is to
# expect the setting expresses an override that a flag defaulting to True could not.
_REQUIRE_PARAMETER_NAME = "require"
_PROHIBIT_PARAMETER_NAME = "prohibit"

# The name given to the single parameter that stands in for the pair, chosen so that it cannot
# collide with a parameter a requirement declares ('_' is not allowed in a requirement's own
# parameter names, and no requirement declares a parameter of this name).
_MODE_PARAMETER_NAME = "mode"

_MODE_SKIP = "skip"
_MODE_REQUIRE = "require"
_MODE_PROHIBIT = "prohibit"

# A boolean that may also be None leaves the expectation to the module, which decides it from
# something the ruleset cannot state (such as the team size). That is a fourth choice rather than a
# value the other three can express.
_MODE_DEFAULT = "use default"

_MODE_CHOICES = [_MODE_SKIP, _MODE_REQUIRE, _MODE_PROHIBIT]

# The neutral choices are grouped ahead of the two that assert something, and 'use default' sits
# beside the states that it resolves to.
_OPTIONAL_MODE_CHOICES = [_MODE_SKIP, _MODE_DEFAULT, _MODE_REQUIRE, _MODE_PROHIBIT]

# What the control states, rather than the name of either parameter it stands in for. The
# requirement it belongs to is displayed immediately above it, so the label does not repeat it.
_MODE_LABEL = "expectation"

# The help text of neither parameter can be reused: each was written to describe a flag being set,
# so it names one of the three states and, for a requirement whose parameter is 'prohibit', names
# the one that is not selected by default.
_MODE_HELP = (
    "Whether the requirement is skipped (skip), enforced as enabled (require), or enforced as "
    "disabled (prohibit)."
)

_OPTIONAL_MODE_HELP = (
    "Whether the requirement is skipped (skip), left to the value the module implies (use "
    "default), enforced as enabled (require), or enforced as disabled (prohibit)."
)

_LIST_DELIMITER = ","

# The states of a tri-state boolean, named so that the control reads as the choice being made rather
# than as a value that happens to be empty.
_OPTIONAL_BOOLEAN_NONE = "default"
_OPTIONAL_BOOLEAN_TRUE = "yes"
_OPTIONAL_BOOLEAN_FALSE = "no"

_OPTIONAL_BOOLEAN_VALUES = {True: _OPTIONAL_BOOLEAN_TRUE, False: _OPTIONAL_BOOLEAN_FALSE}

# A parameter that a module requires but declares a default for (so that its absence is reported by
# the module rather than by the command line) says so at the beginning of its help text.
_REQUIRED_HELP_PREFIX = "[REQUIRED]"


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class _ModeParameters:
    """The pair of parameters that a single mode control stands in for."""

    toggle_name: str
    boolean_name: str

    # An opt-in requirement is included by the toggle being set; an opt-out one by its being clear.
    toggle_includes: bool

    # A 'prohibit' boolean states the negation of what the mode names, so the value written for it
    # is inverted with respect to a 'require' boolean.
    boolean_prohibits: bool

    # A boolean that may also be None can defer the expectation to the module, which is a choice the
    # control offers in addition to the three that a plain boolean can express.
    boolean_allows_none: bool = False


# ----------------------------------------------------------------------
def _GetModeParameters(
    dynamic_parameters: DynamicParameters,
    module_name: str,
    requirement_name: str,
) -> _ModeParameters | None:
    """Return the parameters a mode control replaces, or None if the requirement does not qualify."""

    toggle: tuple[str, bool] | None = None
    boolean: tuple[str, bool, bool] | None = None
    others = 0

    for name, parameter in dynamic_parameters.dynamic_parameters.items():
        argument_info = dynamic_parameters.argument_lookup[name]

        if argument_info.module_name != module_name or argument_info.requirement_name != requirement_name:
            continue

        parameter_name = argument_info.parameter_name

        allows_none = _AllowsNone(parameter.type)
        field_type = _ResolveFieldType(_ResolveType(parameter.type), allows_none=allows_none)

        # A boolean that may also be None contributes a further state rather than disqualifying the
        # requirement, so both kinds of boolean are folded in.
        is_boolean = field_type in (FieldType.Boolean, FieldType.OptionalBoolean)

        # Whether the requirement runs is not a question the module can answer on its behalf, so a
        # toggle is only ever a plain boolean.
        if (
            parameter_name in (_INCLUDE_PARAMETER_NAME, _SKIP_PARAMETER_NAME)
            and field_type == FieldType.Boolean
        ):
            toggle = (name, parameter_name == _INCLUDE_PARAMETER_NAME)
        elif parameter_name in (_REQUIRE_PARAMETER_NAME, _PROHIBIT_PARAMETER_NAME) and is_boolean:
            boolean = (name, parameter_name == _PROHIBIT_PARAMETER_NAME, allows_none)
        else:
            others += 1

    # A requirement qualifies only when the pair is all it has. One with a further parameter states
    # something the modes cannot express, so it keeps the controls that can express it.
    if toggle is None or boolean is None or others != 0:
        return None

    return _ModeParameters(
        toggle[0],
        boolean[0],
        toggle_includes=toggle[1],
        boolean_prohibits=boolean[1],
        boolean_allows_none=boolean[2],
    )


# ----------------------------------------------------------------------
def _CreateModeLookup(
    dynamic_parameters: DynamicParameters,
) -> dict[tuple[str, str | None], _ModeParameters]:
    """Return the mode parameters of every requirement that qualifies, keyed by module and requirement."""

    # A module's own parameters are not a requirement's expectation, so only requirements are
    # considered.
    requirements = {
        (argument_info.module_name, argument_info.requirement_name)
        for argument_info in dynamic_parameters.argument_lookup.values()
        if argument_info.requirement_name is not None
    }

    results: dict[tuple[str, str | None], _ModeParameters] = {}

    for module_name, requirement_name in requirements:
        assert requirement_name is not None

        mode_parameters = _GetModeParameters(dynamic_parameters, module_name, requirement_name)

        if mode_parameters is not None:
            results[(module_name, requirement_name)] = mode_parameters

    return results


# ----------------------------------------------------------------------
def _CreateModeField(
    dynamic_parameters: DynamicParameters,
    arguments: dict[str, dict[str | None, dict[str, object]]],
    argument_info: ArgumentInfo,
    mode_parameters: _ModeParameters,
    *,
    toggle_value: object,
) -> FormField:
    boolean_info = dynamic_parameters.argument_lookup[mode_parameters.boolean_name]

    boolean_value = (
        arguments.get(argument_info.module_name, {})
        .get(argument_info.requirement_name, {})
        .get(
            boolean_info.parameter_name,
            dynamic_parameters.dynamic_parameters[mode_parameters.boolean_name].default,
        )
    )

    allows_none = mode_parameters.boolean_allows_none

    return FormField(
        name=f"{argument_info.module_name}_{argument_info.requirement_name}_{_MODE_PARAMETER_NAME}",
        label=_MODE_LABEL,
        type=FieldType.RequirementMode,
        value=_CreateModeValue(mode_parameters, toggle_value, boolean_value),
        help=_OPTIONAL_MODE_HELP if allows_none else _MODE_HELP,
        choices=list(_OPTIONAL_MODE_CHOICES if allows_none else _MODE_CHOICES),
    )


# ----------------------------------------------------------------------
def _CreateModeValue(
    mode_parameters: _ModeParameters,
    toggle_value: object,
    boolean_value: object,
) -> str:
    """Return the mode that a pair of parameter values expresses."""

    included = bool(toggle_value) if mode_parameters.toggle_includes else not bool(toggle_value)

    # Whether the requirement runs is decided before what it expects, so a skipped requirement reads
    # as skipped whatever the boolean holds.
    if not included:
        return _MODE_SKIP

    # An absent value states no expectation of the user's own, which leaves the one the module
    # implies. The negation a 'prohibit' parameter applies does not apply to the absence of a value.
    if mode_parameters.boolean_allows_none and boolean_value is None:
        return _MODE_DEFAULT

    requires = not bool(boolean_value) if mode_parameters.boolean_prohibits else bool(boolean_value)

    return _MODE_REQUIRE if requires else _MODE_PROHIBIT


# ----------------------------------------------------------------------
def _CreateModeValues(mode_parameters: _ModeParameters, mode: object) -> dict[str, bool | None]:
    """Return the parameter values that a mode expresses, keyed by full parameter name."""

    # A value naming none of the modes leaves the requirement out, which is the choice that asserts
    # nothing about the repository. 'use default' runs the requirement without stating what it
    # expects, so it is included among the modes that do.
    included = mode in (_MODE_REQUIRE, _MODE_PROHIBIT, _MODE_DEFAULT)
    requires = mode == _MODE_REQUIRE

    boolean_value: bool | None

    # A skipped requirement states no expectation either, so the absent value is what pairs with it;
    # were it False, re-including the requirement would show an expectation the user never chose.
    if mode_parameters.boolean_allows_none and mode in (_MODE_DEFAULT, _MODE_SKIP):
        boolean_value = None
    else:
        boolean_value = not requires if mode_parameters.boolean_prohibits else requires

    return {
        mode_parameters.toggle_name: included if mode_parameters.toggle_includes else not included,
        mode_parameters.boolean_name: boolean_value,
    }


# ----------------------------------------------------------------------
def _CreateContainer[ContainerT: FormContainer](
    container_type: type[ContainerT],
    name: str,
    fields: list[FormField],
    description: str,
    **kwargs: object,
) -> ContainerT:
    # Modules and requirements alike contribute exactly one of these, unless it was folded into a
    # mode control, which governs whether the requirement runs in the toggle's place.
    toggle = next(
        (
            field
            for field in fields
            if field.label in (_INCLUDE_PARAMETER_NAME, _SKIP_PARAMETER_NAME)
            and field.type == FieldType.Boolean
        ),
        None,
    )

    if toggle is not None:
        return container_type(
            name,
            fields,
            description,
            toggle=toggle.name,
            toggle_includes=toggle.label == _INCLUDE_PARAMETER_NAME,
            **kwargs,
        )

    mode = next((field for field in fields if field.type == FieldType.RequirementMode), None)

    return container_type(
        name,
        fields,
        description,
        toggle=None if mode is None else mode.name,
        # A mode names the state it selects rather than a flag that is set, so what indicates
        # inclusion is the value itself rather than the polarity of a checkbox.
        toggle_includes=False,
        **kwargs,
    )


# ----------------------------------------------------------------------
def _CreateField(
    name: str,
    label: str,
    parameter: TyperParameter,
    value: object,
) -> FormField:
    resolved_type = _ResolveType(parameter.type)
    field_type = _ResolveFieldType(resolved_type, allows_none=_AllowsNone(parameter.type))
    info = parameter.info

    help_text = getattr(info, "help", None) or ""

    # The display decorates the field rather than repeating the prefix within the help text.
    required = help_text.startswith(_REQUIRED_HELP_PREFIX)
    if required:
        help_text = help_text[len(_REQUIRED_HELP_PREFIX) :].strip()

    choices: list[str] = []

    if field_type == FieldType.Choice:
        assert issubclass(resolved_type, enum.Enum), resolved_type

        choices = [member.value for member in resolved_type]
        value = value.value if isinstance(value, enum.Enum) else value
    elif field_type == FieldType.List:
        # A control is addressed by a single string, so the items of a list are displayed and
        # submitted as one comma-delimited value.
        value = _LIST_DELIMITER.join(str(item) for item in value) if isinstance(value, list | tuple) else ""
    elif field_type == FieldType.Boolean:
        value = bool(value)
    elif field_type == FieldType.OptionalBoolean:
        # The three states are displayed as the strings that identify them, so the control submits
        # the absent value rather than collapsing it to one of the other two.
        choices = [_OPTIONAL_BOOLEAN_NONE, _OPTIONAL_BOOLEAN_TRUE, _OPTIONAL_BOOLEAN_FALSE]
        value = _OPTIONAL_BOOLEAN_NONE if value is None else _OPTIONAL_BOOLEAN_VALUES[bool(value)]
    elif value is None:
        value = ""

    return FormField(
        name=name,
        label=label,
        type=field_type,
        value=value,
        help=help_text,
        choices=choices,
        minimum=getattr(info, "min", None),
        maximum=getattr(info, "max", None),
        # A parameter with no default cannot be satisfied by omitting it.
        required=required or parameter.default is inspect.Parameter.empty,
    )


# ----------------------------------------------------------------------
def _ResolveType(parameter_type: type | UnionType) -> type:
    """Return the meaningful type of an optional parameter (e.g. 'str' for 'str | None')."""

    if isinstance(parameter_type, UnionType):
        return next(
            (arg for arg in get_args(parameter_type) if arg is not type(None)),
            str,
        )

    return parameter_type


# ----------------------------------------------------------------------
def _ResolveFieldType(resolved_type: type, *, allows_none: bool = False) -> FieldType:
    if get_origin(resolved_type) in (list, tuple):
        return FieldType.List

    if isinstance(resolved_type, type) and issubclass(resolved_type, enum.Enum):
        return FieldType.Choice

    if resolved_type is bool:
        # Every other type recovers None from an empty control, which a checkbox does not have.
        return FieldType.OptionalBoolean if allows_none else FieldType.Boolean

    if resolved_type is int:
        return FieldType.Integer

    if resolved_type is float:
        return FieldType.Number

    return FieldType.Text


# ----------------------------------------------------------------------
def _CoerceValue(parameter: TyperParameter, value: object) -> object:
    resolved_type = _ResolveType(parameter.type)
    field_type = _ResolveFieldType(resolved_type, allows_none=_AllowsNone(parameter.type))

    if field_type == FieldType.Boolean:
        return bool(value)

    if field_type == FieldType.OptionalBoolean:
        # A value that names none of the states is the absent one, so a control that was never set
        # resolves to None rather than to one of the values it could have held.
        if value in (True, False):
            return value

        return {
            _OPTIONAL_BOOLEAN_TRUE: True,
            _OPTIONAL_BOOLEAN_FALSE: False,
        }.get(str(value))

    if field_type == FieldType.List:
        items = (
            list(value)
            if isinstance(value, list | tuple)
            else [item for item in (item.strip() for item in str(value).split(_LIST_DELIMITER)) if item]
        )

        # An empty control means the value was not provided, which is distinct from an empty list.
        if not items:
            if _AllowsNone(parameter.type):
                return None

            if parameter.default is not inspect.Parameter.empty:
                return parameter.default

        item_types = get_args(resolved_type)
        item_type = item_types[0] if item_types else str

        return [item_type(item) for item in items]

    if field_type == FieldType.Choice:
        return resolved_type(value)

    # An empty control means the value was not provided. Modules distinguish a missing value from
    # the empty string (raising when a required value is absent), so the parameter's own default is
    # restored rather than coercing the empty string to the parameter's type.
    if value in (None, ""):
        if _AllowsNone(parameter.type):
            return None

        if parameter.default is not inspect.Parameter.empty:
            return parameter.default

    # The form submits every value as a string, so the string is what is converted; a value that is
    # not a number raises, which is reported to the page.
    if field_type == FieldType.Integer:
        return int(str(value))

    if field_type == FieldType.Number:
        return float(str(value))

    return str(value)


# ----------------------------------------------------------------------
def _AllowsNone(parameter_type: type | UnionType) -> bool:
    return isinstance(parameter_type, UnionType) and type(None) in get_args(parameter_type)
