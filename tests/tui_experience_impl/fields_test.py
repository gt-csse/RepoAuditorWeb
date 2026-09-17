import pytest

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Checkbox, Input, Label, Select
from textual.widgets.select import NoSelection

from RepoAuditorWeb.lib.form import FieldType, FormField
from RepoAuditorWeb.tui_experience_impl.fields import CreateControlId, CreateField, CreateValues


# ----------------------------------------------------------------------
def _CreateFormField(
    field_type: FieldType,
    value: object,
    *,
    name: str = "MyModule_one",
    label: str = "one",
    choices: list[str] | None = None,
    help_text: str = "",
    required: bool = False,
) -> FormField:
    return FormField(
        name=name,
        label=label,
        type=field_type,
        value=value,
        help=help_text,
        choices=choices or [],
        required=required,
    )


# ----------------------------------------------------------------------
# A widget resolves its content against the application that displays it, so the controls are
# mounted rather than inspected on their own.
class _FieldApp(App):
    def __init__(self, fields: list[FormField]) -> None:
        super().__init__()

        self.fields = fields

    def compose(self) -> ComposeResult:
        for field in self.fields:
            yield CreateField(field)


# ----------------------------------------------------------------------
async def _Mount(field: FormField) -> tuple[Widget, Label | None]:
    """Mount the field and return its control, along with the label that precedes it."""

    app = _FieldApp([field])

    async with app.run_test():
        control = app.query_one(f"#{CreateControlId(field.name)}")

        if isinstance(control, Checkbox):
            return control, None

        container = control.parent
        assert isinstance(container, Vertical)

        label = container.children[0]
        assert isinstance(label, Label)

        return control, label


# ----------------------------------------------------------------------
class TestCreateControlId:
    # ----------------------------------------------------------------------
    # A parameter name is not a valid Textual id on its own, so it is prefixed.
    def test_NameIsPrefixed(self):
        assert CreateControlId("MyModule_one") == "field-MyModule_one"


# ----------------------------------------------------------------------
class TestCreateField:
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Boolean(self):
        control, label = await _Mount(_CreateFormField(FieldType.Boolean, True))

        assert isinstance(control, Checkbox)
        assert control.value is True
        assert control.id == "field-MyModule_one"

        # A checkbox states its own label, so it is not preceded by one.
        assert label is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_BooleanLabelsItself(self):
        control, _ = await _Mount(_CreateFormField(FieldType.Boolean, False, label="skip"))

        assert isinstance(control, Checkbox)
        assert str(control.label) == "skip"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Text(self):
        control, label = await _Mount(_CreateFormField(FieldType.Text, "my value"))

        assert isinstance(control, Input)
        assert control.value == "my value"
        assert control.type == "text"
        assert label is not None

    # ----------------------------------------------------------------------
    # A value that was never provided displays as an empty control.
    @pytest.mark.asyncio
    async def test_TextWithoutAValue(self):
        control, _ = await _Mount(_CreateFormField(FieldType.Text, None))

        assert isinstance(control, Input)
        assert control.value == ""

    # ----------------------------------------------------------------------
    # Restricting what may be typed reports a bad value at the control rather than once the run
    # begins.
    @pytest.mark.asyncio
    async def test_Integer(self):
        control, _ = await _Mount(_CreateFormField(FieldType.Integer, 5))

        assert isinstance(control, Input)
        assert control.value == "5"
        assert control.type == "integer"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Number(self):
        control, _ = await _Mount(_CreateFormField(FieldType.Number, 1.5))

        assert isinstance(control, Input)
        assert control.value == "1.5"
        assert control.type == "number"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Choice(self):
        control, _ = await _Mount(
            _CreateFormField(FieldType.Choice, "two", choices=["one", "two"]),
        )

        assert isinstance(control, Select)
        assert control.value == "two"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_OptionalBoolean(self):
        control, _ = await _Mount(
            _CreateFormField(FieldType.OptionalBoolean, "default", choices=["default", "yes", "no"]),
        )

        assert isinstance(control, Select)
        assert control.value == "default"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_RequirementMode(self):
        control, _ = await _Mount(
            _CreateFormField(
                FieldType.RequirementMode,
                "require",
                choices=["skip", "require", "prohibit"],
            ),
        )

        assert isinstance(control, Select)
        assert control.value == "require"

    # ----------------------------------------------------------------------
    # A value naming none of the choices leaves the control unresolved rather than selecting one the
    # user never chose.
    @pytest.mark.asyncio
    async def test_ChoiceWithAValueThatIsNotAChoice(self):
        control, _ = await _Mount(
            _CreateFormField(FieldType.Choice, "three", choices=["one", "two"]),
        )

        assert isinstance(control, Select)
        assert isinstance(control.value, NoSelection)

    # ----------------------------------------------------------------------
    # A parameter that cannot be satisfied by omitting it is marked.
    @pytest.mark.asyncio
    async def test_RequiredIsMarked(self):
        _, label = await _Mount(_CreateFormField(FieldType.Text, "", required=True))

        assert label is not None
        assert str(label.content) == "one *"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_NotRequiredIsNotMarked(self):
        _, label = await _Mount(_CreateFormField(FieldType.Text, ""))

        assert label is not None
        assert str(label.content) == "one"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_HelpBecomesATooltip(self):
        control, _ = await _Mount(_CreateFormField(FieldType.Text, "", help_text="My help."))

        assert control.tooltip == "My help."

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_NoHelpIsNoTooltip(self):
        control, _ = await _Mount(_CreateFormField(FieldType.Text, ""))

        assert control.tooltip is None


# ----------------------------------------------------------------------
class TestCreateValues:
    # ----------------------------------------------------------------------
    @staticmethod
    async def _CreateValues(fields: list[FormField]) -> dict[str, object]:
        app = _FieldApp(fields)

        async with app.run_test():
            controls = {widget.id: widget for widget in app.query(".field-control") if widget.id is not None}

            return CreateValues(fields, controls)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Checkbox(self):
        assert await self._CreateValues([_CreateFormField(FieldType.Boolean, True)]) == {
            "MyModule_one": True,
        }

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Input(self):
        assert await self._CreateValues([_CreateFormField(FieldType.Text, "my value")]) == {
            "MyModule_one": "my value",
        }

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_Select(self):
        fields = [_CreateFormField(FieldType.Choice, "two", choices=["one", "two"])]

        assert await self._CreateValues(fields) == {"MyModule_one": "two"}

    # ----------------------------------------------------------------------
    # A control that was never resolved to a choice submits the empty value, which every field type
    # recovers its own default from.
    @pytest.mark.asyncio
    async def test_SelectWithoutAChoice(self):
        fields = [_CreateFormField(FieldType.Choice, "three", choices=["one", "two"])]

        assert await self._CreateValues(fields) == {"MyModule_one": ""}

    # ----------------------------------------------------------------------
    # A field whose control is not displayed contributes nothing, so the value the run started with
    # is what the parameter keeps.
    def test_FieldWithoutAControlIsOmitted(self):
        assert CreateValues([_CreateFormField(FieldType.Text, "")], {}) == {}

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_MultipleFields(self):
        fields = [
            _CreateFormField(FieldType.Text, "my value", name="MyModule_one", label="one"),
            _CreateFormField(FieldType.Boolean, True, name="MyModule_two", label="two"),
        ]

        assert await self._CreateValues(fields) == {
            "MyModule_one": "my value",
            "MyModule_two": True,
        }
