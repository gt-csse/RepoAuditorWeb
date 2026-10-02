---
type: Change
title: Replaced CLAUDE.md with AGENTS.md
description: Replaced the Claude-specific CLAUDE.md agent instructions with a vendor-neutral AGENTS.md based on python_development guidance version 0.9.0.
tags: [agents, ai-assistants, configuration, guidance]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T15:59:41Z }
resource: AGENTS.md
sources:
  - id: agents-md
    resource: https://agents.md/
    title: AGENTS.md
    author: AGENTS.md contributors
---

# Summary

Removed `CLAUDE.md` and added `AGENTS.md`, which carries the repository's coding-agent instructions updated from guidance version 0.2.0 to `python_development` version 0.9.0.

# Motivation

`AGENTS.md` is a vendor-neutral convention read by multiple coding agents, whereas `CLAUDE.md` targets a single tool. The updated guidance also captures conventions that the previous version did not, so agents produce code that matches the repository's practices.

# Changes

- Deleted `CLAUDE.md`.
- Added `AGENTS.md` with the following additions relative to the previous instructions:
  - Restricts generation of `docs/changes` files to the `prepare-pr` skill.
  - Prohibits suppressing static analysis/linting errors.
  - Requires running Python tasks via `uv`.
  - Adds type annotation rules (use `object` instead of `Any`; never introduce `from __future__ import annotations`).
  - Adds dependency management rules using `uv add`, `uv add --dev`, and `uv add --upgrade`.
