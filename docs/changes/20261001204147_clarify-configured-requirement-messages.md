---
type: Change
title: Clarified that requirement error messages reflect configured values
description: Requirement error contexts now state what the requirement was configured to require or prohibit.
tags: [requirement, messages, plugins, github, community-standards]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-01T20:41:47Z }
resource: src/RepoAuditorWeb/lib/plugins
---

# Summary

Reworded the error context returned by requirements from "the requirement specifies it must be ..." / "the requirement prohibits it" to "the requirement was configured to require ..." / "the requirement was configured to prohibit ...".

# Motivation

Expected values can be overridden through configuration, and rationales are now omitted when defaults are overridden. The previous wording implied the expectation was intrinsic to the requirement; the new wording makes clear the failure is measured against the configured value.

# Changes

- Updated error contexts in all GitHub standard, ruleset, default branch, and classic branch protection requirements, plus `FileExistsRequirement`.
- Updated the corresponding test assertions to match the new messages.
