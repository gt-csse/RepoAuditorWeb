---
type: Change
title: Web Execute button is disabled while every module is skipped
description: The web form disables Execute and displays a red error beside the buttons whenever no module is included, so an audit cannot run without auditing anything.
tags: [web, ui, form, validation]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-02T19:15:12Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

Whenever every module in the web form is skipped, or no module exists, the Execute button is disabled and "Include at least one module to execute." is displayed in red beside it. The check runs when the page loads, whenever the form changes, and when a run ends.

# Motivation

A run without a module produces no results, which reads as a clean audit rather than as nothing having been audited. Disabling Execute up front makes the problem visible before the user tries to run.

# Changes

- Added `RefreshExecuteButton`, which disables Execute and shows the error while `IsIncluded` holds for no module. It reads the toggles' state rather than the pills' classes, so it shares the pills' rule without depending on their markup.
- `SetRunning` defers to `RefreshExecuteButton` once a run ends instead of re-enabling Execute unconditionally.
- `Execute` returns immediately while the button is disabled, covering runs started by `config.execute`.
- Added a `#status.error` style using `--error`.
- Added `test_ExecuteRequiresAModule` to the page tests.

# Compatibility

- Web page only; no API or result changes.
