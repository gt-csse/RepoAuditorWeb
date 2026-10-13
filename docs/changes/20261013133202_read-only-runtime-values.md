---
type: Change
title: Made common option values provided at runtime read-only in the interactive experiences
description: Values for --url, --pat, and --branch provided on the command line or in a config file are displayed but cannot be changed in the web and TUI experiences; values from environment variables remain editable.
tags: [feature, web, tui, form, cli]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T13:32:02Z }
resource: src/RepoAuditorWeb/lib/form.py
---

# Summary

Common options (`--url`, `--pat`, `--branch`) explicitly provided on the command line or through a config file are now locked in the `web` and `tui` experiences. Each locked control displays the reason it cannot be changed, and submitted values for locked parameters are replaced by the runtime value.

# Motivation

A common option is applied to every module that does not provide its own value. When a user names the repository to audit at launch, editing that value for a single module within an interactive experience would cause modules to audit different repositories or branches. Locking the value ensures that all plugins operate on the same value. Environment variables act as defaults rather than an explicit request, so they remain editable.

# Changes

## Entry point

- `EntryPoint` inspects the parameter source of each common option; values whose source is `COMMANDLINE` or `DEFAULT_MAP` (typer-config applies config files through the default map) are collected into a `read_only` mapping keyed by dynamic parameter name.
- A module-specific value (for example, `--GitHub-url`) takes precedence over the common option, so that module's field is not locked.
- `read_only` is passed to every experience; the `console` and `json` experiences accept and ignore it.

## Form

- `FormField.read_only_reason` describes why a value cannot be changed; it is empty for editable fields.
- `CreateGroups` accepts `read_only`, displays the read-only value, and sets the reason.
- `ParseValues` accepts `read_only` and uses those values regardless of what was submitted, since the display restriction does not bind a submission.

## Web experience

- Read-only text inputs are rendered with the `readonly` attribute and a lock badge containing the reason, referenced by `aria-describedby` and repeated in the control's `title`.
- `CreateApp` and the run thread pass `read_only` to `CreateGroups` and `ParseValues`.

## TUI experience

- Read-only controls are disabled, and the reason is appended to the label.
- `AuditorApp` passes `read_only` to `CreateGroups` and `ParseValues`.

## Documentation and tests

- README documents which sources produce read-only values.
- Tests cover read-only detection for command line, config file, and environment variable sources; field creation and parsing in `form`; and TUI control rendering.

# Compatibility

- `FormField` serializes an additional `read_only_reason` property.
- Experience `ExecuteExperience` functions accept a new keyword-only `read_only` parameter.
