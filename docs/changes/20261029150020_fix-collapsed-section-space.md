---
type: Change
title: Collapsed web form sections no longer leave blank space beneath them
description: The web form hides the contents of collapsed sections so WebKit stops reserving their height after the labels are measured.
tags: [web, bug, css, webkit]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-29T15:00:20Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The web form's stylesheet now sets `display: none` on every child of a collapsed `<details>` section other than its `<summary>`. Collapsed module, query, and requirement sections now take up only the height of their heading.

# Motivation

Measuring the labels briefly opens and closes every section. Afterward, WebKit, the engine behind the macOS app window, kept reserving the height of each collapsed section's contents, which left large blank gaps in the form.

# Changes

- `src/RepoAuditorWeb/web_experience_impl/page.py`: added the `#form details:not([open]) > :not(summary) { display: none; }` rule to the page style.
- `tests/web_experience_impl/page_test.py`: added `test_CollapsedSectionsReserveNoSpace`, which asserts that the rule is present in the generated page.

# Compatibility

- Visual only; no change to form values or behavior.
