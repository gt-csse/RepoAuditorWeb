---
type: Change
title: Web include and skip controls are switches in each header
description: Each module and requirement header in the web form has a switch that decides whether it runs, replacing the included/skipped pill, and a requirement's require/prohibit setting is a normal field with its own help.
tags: [web, ui, form, switch, css]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-24T17:05:49Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

Whether a module or requirement runs is now a switch at the trailing edge of its header, which can be changed while the container is collapsed. The switch is on while the container runs, whether its field is phrased as 'include' or 'skip'. Module switches are larger and full strength; requirement switches are smaller and faded, and turn gray when their module does not run. A requirement's `require` or `prohibit` setting is no longer an "expectation" dropdown; it is displayed like any other parameter, as a checkbox labeled with its name (or a default/yes/no control when it may be absent), with its own help text.

# Motivation

The main goal is to simplify both the experience and the code. For the user, one switch in the header turns a module or requirement on or off without expanding it, and the remaining settings match the command line's flags and help text rather than a separate dropdown with generic help. For the code, merging 'skip' into the dropdown required pairing logic on the server, special cases on the page, and extra handling to recover a skipped requirement's expectation; once 'skip' moved to the header, the dropdown stood for a single boolean, so the whole "mode" concept could be removed. The result is a net reduction of roughly 700 lines.

# Changes

- `lib/form.py`: removed the code that merged a requirement's skip and require/prohibit settings into one dropdown (`_ModeParameters`, `_GetModeParameters`, `_CreateModeLookup`, `_CreateModeValue(s)`) and the requirement mode field (`FieldType.RequirementMode`, `_CreateModeField`, and the `_MODE_*` constants). Every parameter is displayed by `_CreateField` and parsed by `_ParseValue`; the container's toggle is always its `include`/`skip` boolean.
- `web_experience_impl/page.py`: replaced `AddPill`/`IsIncluded` with `CreateSwitch`, which renders the toggle field as a switch in the summary; added switch CSS; removed the unused `data-toggle` attribute and the `requirement_mode` control.
- Updated form, page, and code-owners requirement tests.

# Compatibility

- Web page change only; no API, result, or CLI changes.
- A `prohibit` checkbox is checked when the setting is prohibited, matching its command-line flag, rather than being presented as a require/prohibit choice.
