---
type: Change
title: Displayed common options in a dedicated section applied to every module
description: The --url, --pat, and --branch values are declared once as common parameters, shown in a Common section of the web and TUI experiences, and applied to every module that declares a parameter of the same name.
tags: [feature, web, tui, form, cli]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T14:16:55Z }
resource: src/RepoAuditorWeb/lib/dynamic_parameters.py
---

# Summary

`--url`, `--pat`, and `--branch` are registered with `DynamicParameters` as common parameters. Modules no longer expose their own options for them; instead, the common values are applied to every module that declares a parameter of the same name. The `web` and `tui` experiences display the values in an expanded `Common` section ahead of the modules, and edits there are used by subsequent runs.

# Motivation

Previously, common values were merged into per-module arguments in `EntryPoint`, so each module also displayed its own editable copy of the value. The per-module copies could diverge from one another, and an edit to one module's copy did not apply to the others. Follows the revert of PR #90, whose read-only approach was rejected.

# Changes

- `DynamicParameters` accepts an optional `common_parameters` mapping, exposed as `common_parameters`; module parameters with those names are not added as module-specific options. Common names may not contain `_`, so they cannot collide with prefixed module parameter names.
- `EntryPoint` registers `url`, `pat`, and `branch` as common parameters, shares their help text with its own options, and passes the values to the experiences as `common_arguments`.
- `Execute` accepts `common_arguments` and applies each value to modules that declare a parameter of that name, overriding any module-level value.
- `form.CreateCommonContainer` and `form.ParseCommonValues` build and parse the `Common` container; value parsing shared with `ParseValues` is extracted into `_ParseValue`.
- The web page and `/fields` endpoint include the `common` container; the web server and TUI retain edited common values between runs.
- README notes that the values apply to every module and appear in the `Common` section.
- Tests cover common parameter registration, application, form creation and parsing, and the web and TUI experiences.

# Compatibility

- Module-specific options such as `--<module>_url` are no longer generated for parameters named `url`, `pat`, or `branch`.
- `Execute`, `server.CreateApp`, `AuditorApp`, and each experience's `ExecuteExperience` require a new positional `common_arguments` parameter.
- `CreatePage` accepts a keyword-only `common` container, and the `/fields` response includes a `common` property.
