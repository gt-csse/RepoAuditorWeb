import json
import re
import textwrap

from RepoAuditorWeb.web_experience_impl.form import FieldType, FormField, FormGroup, FormSection
from RepoAuditorWeb.web_experience_impl.page import CreatePage


# ----------------------------------------------------------------------
_GROUPS = [
    FormGroup(
        "MyModule",
        [FormField("MyModule_value", "value", FieldType.Text, "")],
        "My module description.",
        toggle="MyModule_skip",
        sections=[
            FormSection(
                "MyRequirement",
                [FormField("MyModule_MyRequirement_value", "value", FieldType.Text, "")],
                "My requirement description.",
                toggle="MyModule_MyRequirement_skip",
            ),
        ],
    ),
]

# The page embeds its configuration as JSON so that the form is built by the script rather than
# rendered server-side; that block is what the assertions below inspect.
_CONFIG_REGEX = re.compile(
    r'<script id="config" type="application/json">(?P<config>.*?)</script>',
    re.DOTALL,
)


# ----------------------------------------------------------------------
def _GetConfig(page: str) -> dict[str, object]:
    match = _CONFIG_REGEX.search(page)
    assert match is not None, page

    return json.loads(match.group("config"))


# ----------------------------------------------------------------------
def test_TokenIsEmbedded():
    assert _GetConfig(CreatePage(_GROUPS, "my_token"))["token"] == "my_token"


# ----------------------------------------------------------------------
def test_GroupsAreEmbedded():
    config = _GetConfig(CreatePage(_GROUPS, "my_token"))

    assert config["groups"] == [
        {
            "name": "MyModule",
            "fields": [
                {
                    "name": "MyModule_value",
                    "label": "value",
                    "type": "text",
                    "value": "",
                    "help": "",
                    "choices": [],
                    "minimum": None,
                    "maximum": None,
                    "required": False,
                },
            ],
            "sections": [
                {
                    "name": "MyRequirement",
                    "fields": [
                        {
                            "name": "MyModule_MyRequirement_value",
                            "label": "value",
                            "type": "text",
                            "value": "",
                            "help": "",
                            "choices": [],
                            "minimum": None,
                            "maximum": None,
                            "required": False,
                        },
                    ],
                    "description": "My requirement description.",
                    "toggle": "MyModule_MyRequirement_skip",
                    "toggle_includes": False,
                },
            ],
            "description": "My module description.",
            "toggle": "MyModule_skip",
            "toggle_includes": False,
        },
    ]


# ----------------------------------------------------------------------
def test_NoExecuteByDefault():
    assert _GetConfig(CreatePage(_GROUPS, "my_token"))["execute"] is False


# ----------------------------------------------------------------------
# Resetting discards what a run produced; the values the user entered are left alone.
def test_ResetClearsTheGeneratedContent():
    page = CreatePage(_GROUPS, "my_token")

    assert 'resetButton.addEventListener("click", Reset)' in page
    assert (
        textwrap.dedent(
            """\
            function Reset() {
              outputSection.hidden = true;
              output.textContent = "";
              resultsSection.hidden = true;
              results.textContent = "";

              RefreshResetButton();
            }
            """,
        )
        in page
    )


# ----------------------------------------------------------------------
# Nothing has been generated when the page loads, so the reset button starts out disabled and is
# only enabled once a run has produced output or results.
def test_ResetIsDisabledWhenThereIsNothingToReset():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            function RefreshResetButton() {
              resetButton.disabled = outputSection.hidden && resultsSection.hidden;
            }
            """,
        )
        in page
    )

    assert "BuildForm();\nRefreshResetButton();" in page

    assert "  if (running) resetButton.disabled = true;\n  else RefreshResetButton();\n" in page


# ----------------------------------------------------------------------
def test_Execute():
    assert _GetConfig(CreatePage(_GROUPS, "my_token", execute=True))["execute"] is True


# ----------------------------------------------------------------------
# A collapsed section displays its summary and nothing else, so the pill must belong to the summary
# for the state of the requirement to remain visible.
def test_PillIsDisplayedBySummary():
    page = CreatePage(_GROUPS, "my_token")

    assert 'pill.className = "pill";' in page
    assert "summary.appendChild(pill);" in page


# ----------------------------------------------------------------------
# A collapsed container displays its summary and nothing else, so the description must belong to
# the summary for it to remain visible.
def test_DescriptionIsDisplayedBySummary():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.indent(
            textwrap.dedent(
                """\
                if (container.description) {
                  const description = document.createElement("span");
                  description.className = "description";
                  description.textContent = container.description;
                  summary.appendChild(description);
                }
                """,
            ),
            "  ",
        )
        in page
    )


# ----------------------------------------------------------------------
# A long description is truncated while the container is collapsed so that the summaries read as
# rows, and displayed in full once it is expanded.
def test_DescriptionWrapsWhenTheContainerIsExpanded():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            .module-fields > summary .description,
            .requirement-fields > summary .description {
              font-size: 12px;
              font-weight: 400;
              color: var(--muted);
              min-width: 0;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }
            """,
        )
        in page
    )

    assert (
        textwrap.dedent(
            """\
            .module-fields[open] > summary .description,
            .requirement-fields[open] > summary .description {
              overflow: visible;
              white-space: normal;
            }
            """,
        )
        in page
    )


# ----------------------------------------------------------------------
# The value of the field may change after the pill is created, so the pill follows it.
def test_PillTracksTheFieldThatGovernsTheContainer():
    page = CreatePage(_GROUPS, "my_token")

    assert 'if (toggle instanceof HTMLSelectElement) return toggle.value !== "skip";' in page
    assert "return container.toggle_includes ? toggle.checked : !toggle.checked;" in page
    assert "const included = IsIncluded(container, toggle);" in page
    assert 'pill.textContent = included ? "included" : "skipped";' in page
    assert 'toggle.addEventListener("change", Refresh);' in page


# ----------------------------------------------------------------------
# A module is displayed expanded so that its fields are apparent; the requirements it holds are
# collapsed so that a module with many of them stays legible.
def test_ModulesAreExpandedAndRequirementsAreCollapsed():
    page = CreatePage(_GROUPS, "my_token")

    assert 'CreateContainer(group, "module-fields", true)' in page
    assert 'CreateContainer(section, "requirement-fields", false)' in page
    assert "details.open = open;" in page


# ----------------------------------------------------------------------
# What a module or requirement expects has no effect while it does not run, so the controls that
# state it are disabled rather than left to be set to no purpose.
def test_ControlsAreDisabledWhenTheContainerDoesNotRun():
    page = CreatePage(_GROUPS, "my_token")

    assert "const disabled = inherited || !IsIncluded(container, toggle);" in page
    assert 'details.classList.toggle("disabled", disabled);' in page
    assert 'details.addEventListener("refresh-disabling", Refresh);' in page


# ----------------------------------------------------------------------
# The toggle is what reverses the state it decides, so disabling it along with the rest would leave
# no way back. A container disabled by the one that holds it is past reversing, so its toggle goes
# with it.
def test_ToggleStaysEnabledUnlessItIsDisabledFromAbove():
    page = CreatePage(_GROUPS, "my_token")

    assert "element.disabled = element === toggle ? inherited : disabled;" in page


# ----------------------------------------------------------------------
# A skipped module runs none of its requirements, so the sections it holds are disabled with it.
def test_SkippedModuleDisablesItsRequirements():
    page = CreatePage(_GROUPS, "my_token")

    assert 'const inherited = details.dataset.inherited === "disabled";' in page
    assert 'nested.dataset.inherited = disabled ? "disabled" : "";' in page
    assert 'nested.dispatchEvent(new Event("refresh-disabling"));' in page


# ----------------------------------------------------------------------
# A module is wired before the sections it holds, which do not exist while it is being built.
def test_DisablingIsWiredOnceTheFormIsBuilt():
    page = CreatePage(_GROUPS, "my_token")

    assert "for (const Wire of pendingDisabling) Wire();" in page
    assert "pendingDisabling.length = 0;" in page


# ----------------------------------------------------------------------
# A run disables every control and enabling them all is what ending it would otherwise do, which
# would revive the controls of a module or requirement that does not run.
def test_EndingARunDoesNotReviveDisabledControls():
    page = CreatePage(_GROUPS, "my_token")

    assert "if (!running) for (const Wire of pendingDisabling) Wire();" in page


# ----------------------------------------------------------------------
# A control that cannot be set is dimmed along with its label, since a label naming an editable
# control is what makes the row look editable.
def test_DisabledControlsAreDimmed():
    page = CreatePage(_GROUPS, "my_token")

    assert ".field :disabled { opacity: 0.5; cursor: default; }" in page
    assert ".field:has(:disabled) > label { opacity: 0.5; }" in page


# ----------------------------------------------------------------------
# A label carries the field's description beneath its name, which makes it taller than the control
# it names, so the two are centered against each other rather than aligned at the top.
def test_ControlsAreCenteredAgainstTheirDescription():
    page = CreatePage(_GROUPS, "my_token")

    assert "align-items: center;" in page
    assert ".field > label { color: var(--fg); }" in page

    # The row centers the control, so a checkbox needs no offset of its own to line up with it.
    assert 'input[type="checkbox"] { width: 16px; height: 16px; margin: 0; }' in page
