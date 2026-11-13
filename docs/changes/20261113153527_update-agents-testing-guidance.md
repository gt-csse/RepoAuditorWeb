---
type: Change
title: Language-agnostic testing guidance in AGENTS.md
description: AGENTS.md is updated to python_development version 0.10.0, which moves general test principles into a top-level Testing section and adds rules on distinct test coverage and shared setup.
tags: [agents, guidance, testing, configuration]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-13T15:35:27Z }
resource: AGENTS.md
---

# Summary

AGENTS.md now carries a language-agnostic `Testing` section, and the Python `Testing` section retains only Python-specific conventions.

# Motivation

Test principles such as asserting functionality and comparing entire strings apply regardless of language, so they belong outside the Python section. The new rules on distinct coverage and shared setup reduce redundant, duplicated tests produced by agents.

# Changes

- Bumped the `python_development` version marker from 0.9.0 to 0.10.0.
- Added a top-level `Testing` section requiring tests that validate functionality, cover distinct behavior, extract repeated setup into fixtures or helpers, never remove code to pass, and compare entire strings.
- Scoped the Python `Testing` section to Python tests and removed the rules now covered by the top-level section.

# Compatibility

- Agent guidance only; no source code or runtime behavior changes.
