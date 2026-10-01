---
type: Change
title: Added context to successful requirement results
description: Successful requirement evaluations now return a context message describing the observed value and the configured expectation.
tags: [requirement, messages, plugins, github, community-standards]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-01T20:58:23Z }
resource: src/RepoAuditorWeb/lib/plugins
---

# Summary

Requirements previously returned `None` as the context of a successful `EvaluateResult`. They now return a message such as "The repository's value is '...', which the requirement was configured to require."

# Motivation

Failures explained the observed value relative to the configured expectation, but successes provided no explanation. Because expectations can be overridden through configuration, a success is only meaningful when it states what was observed and what was configured.

# Changes

- Added success contexts to all GitHub standard, ruleset, default branch, and classic branch protection requirements.
- `FileExistsRequirement` reports where the file was found, or the searched directories when the file is prohibited and absent.
- Updated the corresponding test assertions to match the new contexts.
