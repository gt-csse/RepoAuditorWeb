---
type: Change
title: Team-size defaults in the review requirements' help
description: RequireReviewFromCodeOwners, RequiredApprovals, and RequireReviewFromSpecificTeams describe the value each expects for every team size when no value is given, in both the command line help and the web form.
tags: [text, help, docs, requirements, team-size, web]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-16T17:09:49Z }
resource: src/RepoAuditorWeb/lib/plugins/github_impl/ruleset_requirements
---

# Summary

The three requirements whose expected value depends on the GitHub module's team size now describe that value as their default. RequiredApprovals and RequireReviewFromSpecificTeams list the value for each team size, and RequireReviewFromCodeOwners states that it is required only for a large team size.

# Motivation

The help said only that the parameter overrode "the value implied by the team size" without saying what that value was, so it was revealed only in the rationale after a run.

# Changes

- Each parameter describes its default in Typer's `show_default`, which the command line help displays as `[default: (...)]`:
  - RequiredApprovals: `0` for `solo`, `1` for `small`, and `2` for `large`.
  - RequireReviewFromSpecificTeams: `0` for `solo`, `0` for `small`, and `1` for `large`.
  - RequireReviewFromCodeOwners: required only for `large`.
- RequiredApprovals and RequireReviewFromSpecificTeams build the described values from their defaults, so they stay in sync with them.
- The web form appends a described default to a field's help as `Default: ...`, including the help of a requirement's mode control, so the default behind 'use default' is visible there.
  - The default is described in `show_default` rather than in the help because the web form replaces RequireReviewFromCodeOwners' help with its mode control's fixed help, so text in the help would never reach the web form for that requirement. `show_default` is also Typer's own place for a default that cannot be stated as a value, so the command line displays it without further changes.
  - The web form previously ignored `show_default`, so it now reads it; this keeps one source for the default in both the command line and the web form, without moving the text into the requirement's description.
- The custom modules guide advises describing a default that is not a single value in `show_default`, which both the command line and the web form display.
- Updated the tests to assert the help and described defaults.

# Compatibility

- No changes to evaluation, defaults, the command line options, or the json experience or its schema; only help text and documentation changed.
