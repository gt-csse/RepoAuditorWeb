"""Translates form fields into Textual controls and those controls back into submitted values."""

from typing import TYPE_CHECKING

from textual.containers import Vertical
from textual.widgets import Checkbox, Input, Label, Select
from textual.widgets.select import NoSelection

from RepoAuditorWeb.lib.form import FieldType

if TYPE_CHECKING:
    from textual.widget import Widget
    from textual.widgets._input import InputType

    from RepoAuditorWeb.lib.form import FormField


# ----------------------------------------------------------------------
def CreateField(field: FormField) -> Widget:
    """Create the control that displays a single field."""

    if field.type == FieldType.Boolean:
        # A checkbox states its own label, so it is not preceded by one.
        return Checkbox(
            _CreateLabel(field),
            value=bool(field.value),
            id=CreateControlId(field.name),
            classes=_CONTROL_CLASS,
            tooltip=field.help or None,
        )

    if field.type in (FieldType.Choice, FieldType.OptionalBoolean, FieldType.RequirementMode):
        control: Widget = Select(
            [(choice, choice) for choice in field.choices],
            value=str(field.value) if field.value in field.choices else Select.NULL,
            # Every choice the value may take is among the choices, so the prompt is only displayed
            # for a value that names none of them.
            allow_blank=True,
            id=CreateControlId(field.name),
            classes=_CONTROL_CLASS,
            tooltip=field.help or None,
        )
    else:
        control = Input(
            value="" if field.value is None else str(field.value),
            id=CreateControlId(field.name),
            classes=_CONTROL_CLASS,
            type=_INPUT_TYPES.get(field.type, "text"),
            tooltip=field.help or None,
        )

    return Vertical(Label(_CreateLabel(field)), control, classes="field")


# ----------------------------------------------------------------------
def CreateValues(fields: list[FormField], controls: dict[str, Widget]) -> dict[str, object]:
    """Collect what each control holds, keyed by the name its field is submitted under."""

    values: dict[str, object] = {}

    for field in fields:
        control = controls.get(CreateControlId(field.name))
        if control is None:
            continue

        values[field.name] = _CreateValue(control)

    return values


# ----------------------------------------------------------------------
def CreateControlId(name: str) -> str:
    """Return the id of the control that displays the named field."""

    return f"{_ID_PREFIX}{name}"


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# A parameter name identifies the field among all modules, but it is not a valid Textual id (which
# must not begin with a digit and is matched by the css), so it is prefixed rather than used as-is.
_ID_PREFIX = "field-"

# The application collects what every control holds, so a control is identified by class rather than
# by the section of the display that encloses it.
_CONTROL_CLASS = "field-control"

# Restricting what may be typed reports a bad value at the control rather than once the run begins.
_INPUT_TYPES: dict[FieldType, InputType] = {
    FieldType.Integer: "integer",
    FieldType.Number: "number",
}


# ----------------------------------------------------------------------
def _CreateLabel(field: FormField) -> str:
    # A parameter that cannot be satisfied by omitting it is marked, matching what the web
    # experience indicates alongside the control.
    return f"{field.label} *" if field.required else field.label


# ----------------------------------------------------------------------
def _CreateValue(control: Widget) -> object:
    if isinstance(control, Checkbox):
        return control.value

    if isinstance(control, Select):
        # A prompt that was never resolved to a choice submits the empty value, which every field
        # type recovers its own default from.
        return "" if isinstance(control.value, NoSelection) else control.value

    assert isinstance(control, Input), control

    return control.value
