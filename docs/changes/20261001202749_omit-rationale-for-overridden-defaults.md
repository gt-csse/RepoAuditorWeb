---
type: Change
title: Omitted requirement rationales when default values are overridden
description: Requirements now return a rationale only when every requirement-specific parameter uses its default value.
tags: [requirement, rationale, plugins, github, community-standards]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-01T20:27:49Z }
resource: src/RepoAuditorWeb/lib/requirement.py
---

# Summary

Added `Requirement.UsesDefaultValues`, which reports whether every requirement-specific parameter in the requirement data matches its default. Each requirement now builds its rationale in a `_CreateRationale` method that returns `None` when any default is overridden.

# Motivation

A rationale justifies a requirement's default behavior. When a user overrides that behavior (for example, with `prohibit`), the rationale argues for the opposite of what is being enforced and is misleading.

# Changes

- New `Requirement.UsesDefaultValues`; gating parameters such as `skip` and `include` are not treated as overrides.
- All GitHub standard, ruleset, default branch, and classic branch protection requirements, plus `FileExistsRequirement`, moved rationale construction into `_CreateRationale`.
- `EvaluateCommitMessage` accepts a rationale factory instead of a precomputed rationale so the decision is deferred to the requirement.
- Tests cover `UsesDefaultValues` and verify that each requirement omits its rationale when overridden.
