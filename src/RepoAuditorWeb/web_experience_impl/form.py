"""Translates dynamic parameters into form fields and form values back into arguments."""

import enum
import inspect

from dataclasses import dataclass, field
from types import UnionType
from typing import get_args, get_origin, TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters, TyperParameter


# ----------------------------------------------------------------------
class FieldType(enum.StrEnum):
    """The control used to display a field."""

    Boolean = "boolean"
    Integer = "integer"
    Number = "number"
    Text = "text"
    Choice = "choice"
    List = "list"


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

    for name, parameter in dynamic_parameters.dynamic_parameters.items():
        argument_info = dynamic_parameters.argument_lookup[name]

        value = (
            arguments.get(argument_info.module_name, {})
            .get(argument_info.requirement_name, {})
            .get(argument_info.parameter_name, parameter.default)
        )

        # A control is addressed by a single string, so the name that identifies the parameter
        # among all modules is what the page submits its value under.
        groups.setdefault(argument_info.module_name, {}).setdefault(
            argument_info.requirement_name,
            [],
        ).append(_CreateField(name, argument_info.parameter_name, parameter, value))

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

    for name, parameter in dynamic_parameters.dynamic_parameters.items():
        argument_info = dynamic_parameters.argument_lookup[name]

        value = _CoerceValue(parameter, values[name]) if name in values else parameter.default

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

_LIST_DELIMITER = ","

# A parameter that a module requires but declares a default for (so that its absence is reported by
# the module rather than by the command line) says so at the beginning of its help text.
_REQUIRED_HELP_PREFIX = "[REQUIRED]"


# ----------------------------------------------------------------------
def _CreateContainer[ContainerT: FormContainer](
    container_type: type[ContainerT],
    name: str,
    fields: list[FormField],
    description: str,
    **kwargs: object,
) -> ContainerT:
    # Modules and requirements alike contribute exactly one of these, so the display can rely on
    # finding it.
    toggle = next(
        field
        for field in fields
        if field.label in (_INCLUDE_PARAMETER_NAME, _SKIP_PARAMETER_NAME) and field.type == FieldType.Boolean
    )

    return container_type(
        name,
        fields,
        description,
        toggle=toggle.name,
        toggle_includes=toggle.label == _INCLUDE_PARAMETER_NAME,
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
    field_type = _ResolveFieldType(resolved_type)
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
def _ResolveFieldType(resolved_type: type) -> FieldType:
    if get_origin(resolved_type) in (list, tuple):
        return FieldType.List

    if isinstance(resolved_type, type) and issubclass(resolved_type, enum.Enum):
        return FieldType.Choice

    if resolved_type is bool:
        return FieldType.Boolean

    if resolved_type is int:
        return FieldType.Integer

    if resolved_type is float:
        return FieldType.Number

    return FieldType.Text


# ----------------------------------------------------------------------
def _CoerceValue(parameter: TyperParameter, value: object) -> object:
    resolved_type = _ResolveType(parameter.type)
    field_type = _ResolveFieldType(resolved_type)

    if field_type == FieldType.Boolean:
        return bool(value)

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
