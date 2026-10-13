---
type: Change
title: Reverted read-only common option values provided at runtime
description: Common option values for --url, --pat, and --branch provided on the command line or in a config file are once again editable in the web and TUI experiences.
tags: [revert, web, tui, form, cli]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T13:45:01Z }
resource: src/RepoAuditorWeb/lib/form.py
---

# Summary

Reverts PR #90 (commit `8b036dd`), which locked common option values provided at runtime in the `web` and `tui` experiences. All fields are editable again, regardless of the source of their value.

# Motivation

The design introduced in PR #90 was rejected. A different approach is expected to follow in a separate change.

# Changes

- `EntryPoint` no longer computes a `read_only` mapping or passes it to the experiences.
- `FormField.read_only_reason` and the `read_only` parameters of `CreateGroups` and `ParseValues` are removed.
- The web experience no longer renders `readonly` inputs or lock badges; the TUI no longer disables controls.
- README text and tests associated with read-only values are removed.
- `docs/changes/20261013133202_read-only-runtime-values.md` is removed.

# Compatibility

- `FormField` no longer serializes a `read_only_reason` property.
- Experience `ExecuteExperience` functions no longer accept the keyword-only `read_only` parameter.
