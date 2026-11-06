import dataclasses
import json
import re
import textwrap

from RepoAuditorWeb.lib.form import FieldType, FormField, FormGroup, FormSection
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
                query="MyQuery",
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
                    "query": "MyQuery",
                },
            ],
            "description": "My module description.",
            "toggle": "MyModule_skip",
            "toggle_includes": False,
        },
    ]


# ----------------------------------------------------------------------
# Values come from the command line, configuration files, and the form, so one that closes the
# element must not escape it.
def test_ValueCannotEndTheConfigElement():
    value = "</script><script>alert(1)</script>"
    groups = [FormGroup("MyModule", [FormField("MyModule_value", "value", FieldType.Text, value)])]

    page = CreatePage(groups, "my_token")

    assert "<script>alert(1)" not in page
    assert _GetConfig(page)["groups"] == [dataclasses.asdict(group) for group in groups]


# ----------------------------------------------------------------------
def test_NoExecuteByDefault():
    assert _GetConfig(CreatePage(_GROUPS, "my_token"))["execute"] is False


# ----------------------------------------------------------------------
def test_IconIsDisplayed():
    page = CreatePage(_GROUPS, "my_token")

    assert '<link rel="icon" type="image/svg+xml" href="/icon.svg">' in page
    assert '<header><h1><img src="/icon.svg" alt="">RepoAuditor</h1></header>' in page


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
              outputTail.textContent = "";
              output.replaceChildren(outputTail);
              resultsSection.hidden = true;
              results.textContent = "";

              RefreshResetButton();
            }
            """,
        )
        in page
    )


# ----------------------------------------------------------------------
# The form's section is named for what it is to the user rather than for the command line's
# arguments, and the page's sections are larger than the queries that share their style.
def test_SectionHeadingsLeadThePage():
    page = CreatePage(_GROUPS, "my_token")

    assert "<h2>Options</h2>" in page
    assert "<h2>Arguments</h2>" not in page
    assert "section > h2 {\n  font-size: 15px;\n" in page


# ----------------------------------------------------------------------
# A run without a module would produce no results, which reads as a clean audit, so Execute is
# disabled and an error is displayed beside the buttons until a module is included.
def test_ExecuteRequiresAModule():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            function RefreshExecuteButton() {
              const noModule = !config.groups.some(
                (group) => !group.toggle || IsIncluded(group, document.getElementById(group.toggle))
              );
            """
        )
        in page
    )
    assert "executeButton.disabled = noModule;" in page
    assert 'status.classList.toggle("error", noModule);' in page
    assert 'status.textContent = noModule ? "Include at least one module to execute." : "";' in page
    assert "#status.error { color: var(--error); }" in page
    assert 'form.addEventListener("change", RefreshExecuteButton);' in page
    assert "RefreshResetButton();\nRefreshExecuteButton();\n" in page


# ----------------------------------------------------------------------
# A module's failure is reported only in the log, so the labels of its errors and warnings are
# highlighted; the message is not, since it may span several lines.
def test_OutputHighlightsErrorAndWarningLabels():
    page = CreatePage(_GROUPS, "my_token")

    assert "const match = /^(\\s*)(ERROR|WARNING):/.exec(line);" in page
    assert "span.textContent = label.slice(indent.length);" in page
    assert "return [indent, span, line.slice(label.length)];" in page
    assert "#output .error, #output .warning { font-weight: 600; }" in page
    assert "#output .error { color: var(--error); }" in page
    assert "#output .warning { color: var(--warning); }" in page


# ----------------------------------------------------------------------
# Output arrives in chunks that may end mid-line, so only the unfinished last line is redrawn rather
# than the whole log, which would slow a long run with every chunk.
def test_OutputAppendsCompleteLinesAndRedrawsOnlyTheTail():
    page = CreatePage(_GROUPS, "my_token")

    assert 'const outputTail = output.appendChild(document.createElement("span"));' in page
    assert "AppendOutput(message.content);" in page
    assert 'const lines = (outputTail.textContent + content).split("\\n");' in page
    assert 'outputTail.before(...lines.flatMap((line) => [...RenderLine(line), "\\n"]));' in page
    assert "outputTail.replaceChildren(...RenderLine(tail));" in page


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
# The form can be several screens long, so its buttons stay at the bottom of the window while it is
# scrolled, beneath the header when they pass it.
def test_ActionsStayInViewWhileTheFormIsScrolled():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            .actions {
              position: sticky;
              bottom: 0;
              z-index: 1;
              display: flex;
              align-items: center;
              gap: 10px;
              margin: 0 calc(-1 * var(--gutter));
              padding: 12px var(--gutter);
              border-top: 1px solid var(--border);
              background: var(--bg);
            }
            """,
        )
        in page
    )

    assert (
        textwrap.dedent(
            """\
            header {
              padding: 12px 20px;
              border-bottom: 1px solid var(--border);
              position: sticky;
              top: 0;
              background: var(--bg);
              /* Above the form's buttons, which also stay in view and pass beneath it on their way out. */
              z-index: 2;
            }
            """,
        )
        in page
    )


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
    assert 'pill.textContent = included ? "included" : "skipped";' in page
    assert 'toggle.addEventListener("change", Refresh);' in page


# ----------------------------------------------------------------------
# A requirement in a skipped module does not run, so its pill says so whatever its own field says.
def test_PillFollowsTheModule():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        'const included = details.dataset.inherited !== "disabled" && IsIncluded(container, toggle);' in page
    )

    # Once for the pill and once for the disabling, so the pill is refreshed alongside the controls.
    assert page.count('details.addEventListener("refresh-disabling", Refresh);') == 2


# ----------------------------------------------------------------------
# A module is displayed expanded so that its fields are apparent; the requirements it holds are
# collapsed so that a module with many of them stays legible.
def test_ModulesAreExpandedAndRequirementsAreCollapsed():
    page = CreatePage(_GROUPS, "my_token")

    assert 'CreateContainer(group, "module-fields", true)' in page
    assert 'CreateContainer(section, "requirement-fields", false)' in page
    assert 'CreateContainer({ name: query, fields: [] }, "query-fields", false)' in page
    assert "details.open = open;" in page


# ----------------------------------------------------------------------
# The requirements of a query are enclosed by a single container for the run of them, which is
# collapsed so that a module with many queries stays legible.
def test_RequirementsAreGroupedByTheirCollapsedQuery():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.indent(
            textwrap.dedent(
                """\
                if (section.query && section.query !== query) {
                  query = section.query;
                  parent = CreateContainer({ name: query, fields: [] }, "query-fields", false);
                  details.appendChild(parent);
                }

                parent.appendChild(CreateContainer(section, "requirement-fields", false));
                """,
            ),
            "      ",
        )
        in page
    )


# ----------------------------------------------------------------------
# Measuring the labels opens and closes every section, after which WebKit keeps reserving the height
# of a collapsed section's contents unless they are removed from the layout.
def test_CollapsedSectionsReserveNoSpace():
    page = CreatePage(_GROUPS, "my_token")

    assert "#form details:not([open]) > :not(summary) { display: none; }" in page


# ----------------------------------------------------------------------
# A query has no toggle of its own, so a module disables the requirements nested within its queries.
def test_ModuleDisablesRequirementsWithinQueries():
    page = CreatePage(_GROUPS, "my_token")

    assert 'details.querySelectorAll(":scope > details, :scope > .query-fields > details")' in page


# ----------------------------------------------------------------------
# The module is the outermost grouping, so its name is set at least as prominently as the queries
# nested within it.
def test_ModuleNameIsMoreProminentThanQueryName():
    page = CreatePage(_GROUPS, "my_token")

    assert ".module-fields > summary { font-size: 17px; padding: 10px 0; }" in page
    assert (
        textwrap.dedent(
            """\
            .module-fields > summary,
            .query-fields > summary { font-weight: 700; }
            """,
        )
        in page
    )
    assert (
        textwrap.dedent(
            """\
            .query-fields > summary {
              margin-left: -12px;
              padding: 8px 0;
              /* Uppercase distinguishes a query from the requirements it holds without competing with the
                 module name in size. */
              font-size: 13px;
              text-transform: uppercase;
              letter-spacing: 0.04em;
            }
            """,
        )
        in page
    )


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

    assert "for (const Wire of pendingDisabling) refreshDisabling.push(Wire());" in page
    assert "pendingDisabling.length = 0;" in page
    assert "refreshDisabling.length = 0;" in page


# ----------------------------------------------------------------------
# A run disables every control and enabling them all is what ending it would otherwise do, which
# would revive the controls of a module or requirement that does not run. The state is refreshed
# rather than rewired so that listeners do not accumulate across runs.
def test_EndingARunDoesNotReviveDisabledControls():
    page = CreatePage(_GROUPS, "my_token")

    assert "if (!running) for (const Refresh of refreshDisabling) Refresh();" in page
    assert "for (const Wire of pendingDisabling) Wire();" not in page


# ----------------------------------------------------------------------
# A control that cannot be set is dimmed along with its label, since a label naming an editable
# control is what makes the row look editable.
def test_DisabledControlsAreDimmed():
    page = CreatePage(_GROUPS, "my_token")

    assert ".field :disabled { opacity: 0.5; cursor: default; }" in page
    assert ".field:has(:disabled) > label { opacity: 0.5; }" in page


# ----------------------------------------------------------------------
# A module or requirement that does not run is muted, so that its state does not have to be read
# from its pill alone.
def test_ContainersThatDoNotRunAreMuted():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            .module-fields.disabled { background: transparent; border-style: dashed; }

            .module-fields.disabled > summary .name,
            .module-fields.disabled .query-fields > summary,
            .requirement-fields.disabled > summary .name { color: var(--skipped); }
            """,
        )
        in page
    )


# ----------------------------------------------------------------------
# A label carries the field's description beneath its name, which makes it taller than the control
# it names, so the two are centered against each other rather than aligned at the top.
def test_ControlsAreCenteredAgainstTheirDescription():
    page = CreatePage(_GROUPS, "my_token")

    assert "align-items: center;" in page
    assert ".field > label { color: var(--fg); }" in page

    # The row centers the control, so a checkbox needs no offset of its own to line up with it.
    assert 'input[type="checkbox"] { width: 16px; height: 16px; margin: 0; }' in page


# ----------------------------------------------------------------------
# The webview disables selection across the page, so the output and results opt back in to it so
# that they can be copied.
def test_OutputAndResultsAreSelectable():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            #output, #results {
              -webkit-user-select: text;
              user-select: text;
              cursor: auto;
            }
            """,
        )
        in page
    )


# ----------------------------------------------------------------------
# Scrolling to new output would move selected text away before it is copied, or extend a selection
# in progress.
def test_OutputDoesNotScrollWhileSelecting():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            function IsSelectingOutput() {
              const selection = getSelection();
              return !selection.isCollapsed && output.contains(selection.anchorNode);
            }
            """,
        )
        in page
    )
    assert "if (atBottom && !IsSelectingOutput()) output.scrollTop = output.scrollHeight;" in page


# ----------------------------------------------------------------------
# The macOS window ignores 'window.open', so a clicked link is marked to open elsewhere and followed.
def test_ClickedLinksOpenElsewhere():
    page = CreatePage(_GROUPS, "my_token")

    assert (
        textwrap.dedent(
            """\
            document.addEventListener("click", (event) => {
              const link = FindLink(event.target);
              if (!link || !/^https?:$/.test(link.protocol)) return;

              linkStatus.hidden = true;

              // The macOS window ignores 'window.open' and hands only a clicked link that opens elsewhere to
              // the browser, so the link is marked to open elsewhere and left to be followed.
              link.target = "_blank";
              link.rel = "noopener";
            });
            """,
        )
        in page
    )
