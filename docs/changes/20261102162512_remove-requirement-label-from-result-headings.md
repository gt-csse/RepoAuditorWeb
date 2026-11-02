---
type: Change
title: Web result headings no longer label requirements as such
description: Each web result heading shows the module and requirement names without the redundant "Requirement" label between them.
tags: [web, ui, results, text]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-02T16:25:12Z }
resource: src/RepoAuditorWeb/web_experience_impl/results_html.py
---

# Summary

Web result headings render the module name followed directly by the requirement name and result badge, dropping the literal "Requirement" text that preceded the requirement name.

# Motivation

Every result is the result of a requirement, so the label added no information and lengthened each heading.

# Changes

- Removed the `Requirement` text from the `<summary>` rendered by `_RenderRequirements`.
- Added `test_RequirementIsNamedWithoutALabel` to the results tests.

# Compatibility

- Visual-only change to the web results; no API or result changes.
