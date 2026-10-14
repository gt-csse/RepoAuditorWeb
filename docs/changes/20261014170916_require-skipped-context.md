---
type: Change
title: Skipped requirement results explain why the requirement did not run
description: EvaluateResult requires context for Skipped results, and Requirement.Evaluate supplies it based on how the requirement was skipped.
tags: [requirements, evaluate-result, skipped, validation]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-14T17:09:16Z }
resource: src/RepoAuditorWeb/lib/requirement.py
---

# Summary

`EvaluateResult` raises `ValueError` when a `Skipped` result has no `context`. `Requirement.Evaluate` now produces a context that distinguishes a requirement skipped by configuration from one that runs only when explicitly included.

# Motivation

A skipped requirement carries no resolution or rationale, so without context a user viewing verbose output could not tell why the requirement did not run. Enforcing the context at construction keeps custom modules from producing unexplained skipped results.

# Changes

- Added `EvaluateResult.__post_init__`, which raises `ValueError("Skipped results must provide context.")` when `result` is `Skipped` and `context` is `None` or empty.
- `Requirement.Evaluate` returns `"The '<name>' requirement was configured to be skipped."` for skipped requirements and `"The '<name>' requirement runs only when explicitly included, and it was not included."` for requirements that require explicit inclusion.
- Documented the `Skipped` context rule in `docs/custom_modules.md`.
- Updated tests that construct `Skipped` results to provide context, and added coverage for the new validation and messages.

# Compatibility

- Breaking for custom modules that construct `EvaluateResult` with `EvaluateResultValue.Skipped` and no context; they must now supply one.
- Experience output for skipped requirements now includes the context.
