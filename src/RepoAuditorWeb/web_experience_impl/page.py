"""Generates the HTML page displayed by the web experience."""

import dataclasses
import json
import textwrap

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from RepoAuditorWeb.web_experience_impl.form import FormGroup


# ----------------------------------------------------------------------
def CreatePage(groups: list[FormGroup], token: str, *, execute: bool = False) -> str:
    """Create the page that displays the form, the execution output, and the results."""

    # The form is built by the page from this data rather than being rendered here so that a single
    # description of each field drives both the initial display and the values that are submitted.
    config = json.dumps(
        {
            "token": token,
            "execute": execute,
            "groups": [dataclasses.asdict(group) for group in groups],
        },
    )

    return textwrap.dedent(
        """\
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="utf-8">
        <title>RepoAuditor</title>
        <style>
        {style}
        </style>
        </head>
        <body>
        <header><h1>RepoAuditor</h1></header>
        <main>
        <section id="arguments">
        <h2>Arguments</h2>
        <form id="form" autocomplete="off"></form>
        <div class="actions">
        <button type="button" id="execute">Execute</button>
        <button type="button" id="reset">Reset</button>
        <span id="status"></span>
        </div>
        </section>
        <section id="output-section" hidden>
        <h2>Output</h2>
        <pre id="output"></pre>
        </section>
        <section id="results-section" hidden>
        <h2>Results</h2>
        <div id="results"></div>
        </section>
        </main>
        <div id="link-status" hidden></div>
        <script id="config" type="application/json">{config}</script>
        <script>
        {script}
        </script>
        </body>
        </html>
        """,
    ).format(style=_STYLE, script=_SCRIPT, config=config)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_STYLE = textwrap.dedent(
    """\
    :root {
      color-scheme: light dark;
      --bg: #ffffff;
      --fg: #1c1c1e;
      --muted: #6b6b70;
      --border: #d8d8dc;
      --panel: #f6f6f8;
      --accent: #0b5fff;
      --success: #1a7f37;
      --warning: #9a6700;
      --error: #c1121f;
      --skipped: #6b6b70;
      /* Distinguishes the rationale from the resolution without implying a result value. */
      --rationale: #7c4dcc;
    }

    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #1c1c1e;
        --fg: #f2f2f7;
        --muted: #9a9aa0;
        --border: #3a3a3c;
        --panel: #262629;
        --accent: #4f8bff;
        --success: #3fb950;
        --warning: #d29922;
        --error: #ff6b6b;
        --skipped: #9a9aa0;
        --rationale: #b48ef5;
      }
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
    }

    header {
      padding: 12px 20px;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      background: var(--bg);
      z-index: 1;
    }

    header h1 { margin: 0; font-size: 16px; letter-spacing: 0.02em; }

    main { padding: 20px; max-width: 1100px; margin: 0 auto; }

    section { margin-bottom: 24px; }

    section > h2 {
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      margin: 0 0 10px;
    }

    .module-fields {
      border: 1px solid var(--border);
      border-radius: 6px;
      margin: 0 0 12px;
      padding: 0 14px 12px;
      background: var(--panel);
    }

    /* A collapsed module leaves only its summary behind, so the padding that separates the summary
       from the border belongs to the summary rather than to the container. */
    .module-fields:not([open]) { padding-bottom: 0; }

    .module-fields > summary { font-size: 15px; padding: 10px 0; }

    /* The label column is as wide as the widest label on the page, measured once the form is built,
       so that labels are not truncated while space is available and the controls of every module
       still line up in a single column. The fallback applies until that measurement is made. */
    #form { --label-width: 220px; }

    .field {
      display: grid;
      grid-template-columns: minmax(0, var(--label-width)) minmax(0, 1fr);
      column-gap: 24px;
      align-items: start;
      padding: 6px 0;
    }

    .field > label { color: var(--fg); padding-top: 5px; }

    .field .help { display: block; color: var(--muted); font-size: 12px; }

    /* A field that must be provided is marked so that it is apparent before the form is submitted. */
    .field .required {
      color: var(--error);
      font-weight: 600;
      margin-left: 3px;
    }

    /* A requirement's fields are indented beneath its name so that they read as belonging to the
       requirement rather than to the module. */
    .requirement-fields {
      border-top: 1px solid var(--border);
      margin-top: 6px;
      padding-left: 12px;
    }

    .requirement-fields > summary { margin-left: -12px; padding: 7px 0; }

    .module-fields > summary,
    .requirement-fields > summary {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      cursor: pointer;
      list-style: none;
    }

    .module-fields > summary::-webkit-details-marker,
    .requirement-fields > summary::-webkit-details-marker { display: none; }

    .module-fields > summary::before,
    .requirement-fields > summary::before {
      content: "";
      width: 0;
      height: 0;
      border-left: 5px solid currentColor;
      border-top: 4px solid transparent;
      border-bottom: 4px solid transparent;
      color: var(--muted);
      transition: transform 0.15s;
    }

    .module-fields[open] > summary::before,
    .requirement-fields[open] > summary::before { transform: rotate(90deg); }

    /* The description accompanies the name rather than competing with it, and yields its width to
       the name and the pill so that neither is displaced by a long one. */
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

    /* A collapsed container is a single row that the summaries above and below it are read against,
       so a long description is truncated there. Once the container is expanded it is the one being
       read, and the whole description matters more than the height of the row it occupies. */
    .module-fields[open] > summary .description,
    .requirement-fields[open] > summary .description {
      overflow: visible;
      white-space: normal;
    }

    /* The marker, the name and the pill remain on the first line of a wrapped description rather
       than being centered against the block it becomes. */
    .module-fields[open] > summary,
    .requirement-fields[open] > summary { align-items: baseline; }

    .module-fields[open] > summary::before,
    .requirement-fields[open] > summary::before { align-self: center; }

    /* The pill is pushed to the trailing edge so that the state of every module and requirement can
       be read down a single column rather than at the end of names of differing length. */
    .module-fields > summary .pill,
    .requirement-fields > summary .pill {
      margin-left: auto;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 2px 8px;
      border: 1px solid currentColor;
      border-radius: 10px;
    }

    .module-fields > summary .pill.included,
    .requirement-fields > summary .pill.included { color: var(--success); }

    .module-fields > summary .pill.skipped,
    .requirement-fields > summary .pill.skipped { color: var(--skipped); }

    input[type="text"], input[type="number"], select {
      width: 100%;
      /* Widening a control past what its value can occupy makes it harder to read, not easier. */
      max-width: 60ch;
      padding: 6px 8px;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--bg);
      color: var(--fg);
      font: inherit;
    }

    input[type="checkbox"] { width: 16px; height: 16px; margin-top: 6px; }

    .actions { display: flex; align-items: center; gap: 10px; }

    button {
      padding: 7px 16px;
      border: 1px solid transparent;
      border-radius: 4px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }

    button#reset { background: transparent; color: var(--fg); border-color: var(--border); }

    button:disabled { opacity: 0.5; cursor: default; }

    #status { color: var(--muted); }

    #output {
      margin: 0;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--panel);
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font: 12px/1.45 ui-monospace, "Cascadia Mono", monospace;
    }

    table.summary { border-collapse: collapse; margin-bottom: 18px; }

    table.summary th, table.summary td {
      border: 1px solid var(--border);
      padding: 5px 12px;
      text-align: left;
    }

    table.summary td { text-align: right; font-variant-numeric: tabular-nums; }

    table.summary tr.success th { color: var(--success); }
    table.summary tr.warning th { color: var(--warning); }
    table.summary tr.error th { color: var(--error); }
    table.summary tr.skipped th, table.summary tr.does_not_apply th { color: var(--skipped); }

    .requirement {
      border: 1px solid var(--border);
      border-left-width: 4px;
      border-radius: 6px;
      padding: 12px 16px;
      margin-bottom: 12px;
      background: var(--panel);
    }

    .requirement.error { border-left-color: var(--error); }
    .requirement.warning { border-left-color: var(--warning); }
    .requirement.success { border-left-color: var(--success); }
    .requirement.skipped, .requirement.does_not_apply { border-left-color: var(--skipped); }

    .requirement > summary {
      font-size: 15px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      cursor: pointer;
      list-style: none;
    }

    /* The default triangle cannot be styled consistently across engines, so it is replaced with a
       marker that rotates to reflect the open state. */
    .requirement > summary::-webkit-details-marker { display: none; }

    .requirement > summary::before {
      content: "";
      width: 0;
      height: 0;
      border-left: 5px solid currentColor;
      border-top: 4px solid transparent;
      border-bottom: 4px solid transparent;
      color: var(--muted);
      transition: transform 0.15s;
    }

    .requirement[open] > summary::before { transform: rotate(90deg); }

    .requirement > summary .name { font-family: ui-monospace, monospace; }

    /* The module a requirement came from is displayed ahead of its name so that results drawn from
       several modules remain attributable. */
    .requirement > summary .module {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
      padding: 2px 8px;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: var(--bg);
    }

    .requirement > summary .badge {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      padding: 2px 8px;
      border-radius: 10px;
      border: 1px solid currentColor;
    }

    .requirement.error > summary .badge { color: var(--error); }
    .requirement.warning > summary .badge { color: var(--warning); }
    .requirement.success > summary .badge { color: var(--success); }
    .requirement.skipped > summary .badge,
    .requirement.does_not_apply > summary .badge { color: var(--skipped); }

    .requirement > .body { margin-top: 10px; }

    /* 'Resolution' (what to do) and 'Rationale' (why it matters) are different kinds of guidance,
       so each is enclosed in its own block. The content is authored as Markdown and brings its own
       headings and emphasis, which a label alone cannot compete with. */
    .requirement .resolution,
    .requirement .rationale {
      margin-top: 14px;
      border: 1px solid var(--border);
      border-left: 3px solid var(--section-accent);
      border-radius: 5px;
      background: var(--bg);
      /* Clips the header's tint to the rounded corners so it meets the border on both edges. */
      overflow: hidden;
    }

    .requirement .resolution { --section-accent: var(--accent); }
    .requirement .rationale { --section-accent: var(--rationale); }

    .requirement .resolution > summary,
    .requirement .rationale > summary {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.10em;
      color: var(--section-accent);
      /* The header spans the block so that it reads as a title bar rather than a first line. */
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 5px 14px;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
      cursor: pointer;
      list-style: none;
    }

    .requirement .resolution > summary::-webkit-details-marker,
    .requirement .rationale > summary::-webkit-details-marker { display: none; }

    .requirement .resolution > summary::before,
    .requirement .rationale > summary::before {
      content: "";
      width: 0;
      height: 0;
      border-left: 5px solid currentColor;
      border-top: 4px solid transparent;
      border-bottom: 4px solid transparent;
      transition: transform 0.15s;
    }

    .requirement .resolution[open] > summary::before,
    .requirement .rationale[open] > summary::before { transform: rotate(90deg); }

    /* A collapsed section leaves no content behind, so the padding belongs to the content itself. */
    .requirement .resolution > .content,
    .requirement .rationale > .content { padding: 10px 14px; }

    /* Markdown headings within the content must stay subordinate to the section title. */
    .requirement .content > :where(h4, h5, h6):first-of-type { margin-top: 0; }

    .requirement h4, .requirement h5, .requirement h6 {
      font-size: 13px;
      margin: 12px 0 4px;
    }

    .requirement p { margin: 6px 0; }

    .requirement ul, .requirement ol { margin: 6px 0; padding-left: 22px; }

    .requirement li { margin: 3px 0; }

    .requirement table { border-collapse: collapse; margin: 8px 0; }

    .requirement th, .requirement td { border: 1px solid var(--border); padding: 4px 10px; }

    .requirement code {
      font-family: ui-monospace, monospace;
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 3px;
      padding: 1px 4px;
    }

    .requirement a { color: var(--accent); }

    .error-message {
      border: 1px solid var(--error);
      border-radius: 6px;
      padding: 10px 14px;
      color: var(--error);
    }

    /* The webview draws no chrome of its own, so the destination of a link is displayed the way a
       browser would display it. */
    #link-status {
      position: fixed;
      bottom: 0;
      left: 0;
      max-width: 90vw;
      padding: 3px 8px;
      border: 1px solid var(--border);
      border-left: none;
      border-bottom: none;
      border-top-right-radius: 4px;
      background: var(--panel);
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      pointer-events: none;
    }
    """,
)


# ----------------------------------------------------------------------
_SCRIPT = textwrap.dedent(
    """\
    const config = JSON.parse(document.getElementById("config").textContent);

    const form = document.getElementById("form");
    const executeButton = document.getElementById("execute");
    const resetButton = document.getElementById("reset");
    const status = document.getElementById("status");
    const outputSection = document.getElementById("output-section");
    const output = document.getElementById("output");
    const resultsSection = document.getElementById("results-section");
    const results = document.getElementById("results");
    const linkStatus = document.getElementById("link-status");

    // Every control is registered with a reader so that collecting the arguments does not depend on
    // the type of control that was created for a field.
    const readers = new Map();

    function CreateControl(field) {
      if (field.type === "boolean") {
        const input = document.createElement("input");
        input.type = "checkbox";
        input.checked = Boolean(field.value);
        readers.set(field.name, () => input.checked);
        return input;
      }

      if (field.type === "choice") {
        const select = document.createElement("select");

        for (const choice of field.choices) {
          const option = document.createElement("option");
          option.value = choice;
          option.textContent = choice;
          option.selected = choice === field.value;
          select.appendChild(option);
        }

        readers.set(field.name, () => select.value);
        return select;
      }

      const input = document.createElement("input");

      if (field.type === "list") {
        input.type = "text";
        // The value is split on commas by the server, so what separates the items is displayed
        // rather than left to be inferred from the value the field started with.
        input.placeholder = "Comma-delimited values";
      } else if (field.type === "integer" || field.type === "number") {
        input.type = "number";
        if (field.type === "integer") input.step = "1";
        if (field.minimum !== null) input.min = field.minimum;
        if (field.maximum !== null) input.max = field.maximum;
      } else {
        input.type = "text";
      }

      input.value = field.value === null || field.value === undefined ? "" : field.value;
      input.required = field.required;
      readers.set(field.name, () => input.value);

      return input;
    }

    function CreateRow(field) {
      const row = document.createElement("div");
      row.className = `field ${field.type}`;

      const label = document.createElement("label");
      label.htmlFor = field.name;
      label.textContent = field.label;

      if (field.required) {
        const marker = document.createElement("span");
        marker.className = "required";
        marker.textContent = "*";
        marker.title = "Required";
        label.appendChild(marker);
      }

      if (field.help) {
        const help = document.createElement("span");
        help.className = "help";
        help.textContent = field.help;
        label.appendChild(help);
      }

      const control = CreateControl(field);
      control.id = field.name;
      control.name = field.name;

      row.appendChild(label);
      row.appendChild(control);

      return row;
    }

    // Whether a module or requirement runs is worth knowing while it is collapsed, so the pill
    // belongs to the summary and tracks the field that governs it rather than reading it once.
    function AddPill(container, summary, toggle) {
      const pill = document.createElement("span");
      pill.className = "pill";
      summary.appendChild(pill);

      const Refresh = () => {
        const included = container.toggle_includes ? toggle.checked : !toggle.checked;
        pill.textContent = included ? "included" : "skipped";
        pill.classList.toggle("included", included);
        pill.classList.toggle("skipped", !included);
      };

      toggle.addEventListener("change", Refresh);
      Refresh();
    }

    // A module and a requirement are displayed the same way; they differ in how prominent they are
    // and in whether the fields they hold are worth showing before they are asked for.
    function CreateContainer(container, className, open) {
      const details = document.createElement("details");
      details.className = className;
      details.open = open;

      const summary = document.createElement("summary");

      const name = document.createElement("span");
      name.className = "name";
      name.textContent = container.name;
      summary.appendChild(name);

      // The description belongs to the summary rather than to the body so that what a module or
      // requirement does is apparent without expanding it.
      if (container.description) {
        const description = document.createElement("span");
        description.className = "description";
        description.textContent = container.description;
        summary.appendChild(description);
      }

      details.appendChild(summary);

      for (const field of container.fields) details.appendChild(CreateRow(field));

      if (container.toggle) {
        AddPill(container, summary, details.querySelector(`#${CSS.escape(container.toggle)}`));
      }

      return details;
    }

    // A label is only as informative as the part of it that is displayed, so the column is widened
    // to hold the longest one instead of truncating them all at a width chosen in advance. The
    // labels of collapsed requirements are measured too, so that expanding one does not shift the
    // column. The share of the form the column may claim is bounded so that the controls remain
    // usable when a label is unreasonably long.
    function RefreshLabelWidth() {
      const available = form.clientWidth;
      if (available === 0) return;

      // A collapsed section does not lay its contents out, so every section is opened for the
      // duration of the measurement and restored afterwards.
      const collapsed = [...form.querySelectorAll("details:not([open])")];
      for (const details of collapsed) details.open = true;

      let widest = 0;

      for (const label of form.querySelectorAll(".field > label")) {
        // 'max-content' reports the width the text wants; the property is set on the element so
        // that the value reflects the styles the label is actually displayed with.
        label.style.width = "max-content";
        widest = Math.max(widest, label.getBoundingClientRect().width);
        label.style.width = "";
      }

      for (const details of collapsed) details.open = false;

      // Rounded up because a fractional measurement can round down to less than the text occupies.
      form.style.setProperty(
        "--label-width",
        `${Math.min(Math.ceil(widest) + 1, Math.round(available * 0.6))}px`,
      );
    }

    function BuildForm() {
      form.textContent = "";
      readers.clear();

      for (const group of config.groups) {
        // A module is displayed expanded; the requirements it holds are collapsed until one is the
        // one the user is interested in.
        const details = CreateContainer(group, "module-fields", true);

        for (const section of group.sections) {
          details.appendChild(CreateContainer(section, "requirement-fields", false));
        }

        form.appendChild(details);
      }

      RefreshLabelWidth();
    }

    // There is nothing to reset until a run has produced something to discard.
    function RefreshResetButton() {
      resetButton.disabled = outputSection.hidden && resultsSection.hidden;
    }

    // The form retains what the user entered; only what a run produced is discarded.
    function Reset() {
      outputSection.hidden = true;
      output.textContent = "";
      resultsSection.hidden = true;
      results.textContent = "";

      RefreshResetButton();
    }

    function CollectArguments() {
      const args = {};
      for (const [name, Read] of readers) args[name] = Read();
      return args;
    }

    function SetRunning(running) {
      executeButton.disabled = running;
      status.textContent = running ? "Executing..." : "";
      for (const element of form.elements) element.disabled = running;

      if (running) resetButton.disabled = true;
      else RefreshResetButton();
    }

    function ShowError(message) {
      resultsSection.hidden = false;
      results.textContent = "";

      const div = document.createElement("div");
      div.className = "error-message";
      div.textContent = message;
      results.appendChild(div);
    }

    function Stream() {
      const source = new EventSource(`/api/stream?token=${encodeURIComponent(config.token)}`);

      source.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === "output") {
          const atBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 40;
          output.textContent += message.content;
          if (atBottom) output.scrollTop = output.scrollHeight;
        } else if (message.type === "results") {
          resultsSection.hidden = false;
          results.innerHTML = message.html;
        } else if (message.type === "error") {
          ShowError(message.message);
        } else if (message.type === "done") {
          source.close();
          SetRunning(false);
        }
      };

      source.onerror = () => {
        source.close();
        SetRunning(false);
      };
    }

    async function Execute() {
      Reset();
      outputSection.hidden = false;

      SetRunning(true);

      try {
        const response = await fetch("/api/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Auditor-Token": config.token },
          body: JSON.stringify({ arguments: CollectArguments() }),
        });

        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          ShowError(body.detail || `The request failed (${response.status}).`);
          SetRunning(false);
          return;
        }
      } catch (ex) {
        ShowError(String(ex));
        SetRunning(false);
        return;
      }

      Stream();
    }

    function FindLink(target) {
      return target instanceof Element ? target.closest("a[href]") : null;
    }

    // The window has no address bar or back button, so the destination of a link is displayed on
    // hover and following one is handed to the browser rather than navigating away from the results.
    document.addEventListener("mouseover", (event) => {
      const link = FindLink(event.target);
      if (!link) return;

      linkStatus.textContent = link.href;
      linkStatus.hidden = false;
    });

    document.addEventListener("mouseout", (event) => {
      if (FindLink(event.target)) linkStatus.hidden = true;
    });

    document.addEventListener("click", (event) => {
      const link = FindLink(event.target);
      if (!link || !/^https?:$/.test(link.protocol)) return;

      event.preventDefault();
      linkStatus.hidden = true;
      window.open(link.href, "_blank");
    });

    executeButton.addEventListener("click", Execute);
    resetButton.addEventListener("click", Reset);

    // The share of the form the column may claim depends on how wide the form is.
    window.addEventListener("resize", RefreshLabelWidth);

    BuildForm();
    RefreshResetButton();

    // The form must exist before its values can be submitted.
    if (config.execute) Execute();
    """,
)
