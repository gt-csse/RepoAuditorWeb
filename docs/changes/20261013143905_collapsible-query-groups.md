---
type: Change
title: Made query groups collapsible in the web form
description: The requirements of each query are enclosed in a collapsed container rather than introduced by a static heading.
tags: [web, ui]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T14:39:06Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

In the web experience, the requirements of a query are enclosed in a collapsible `query-fields` container, collapsed by default, instead of following a static `query-heading` divider.

# Motivation

A module with many queries produced a long, flat list of requirements. Collapsing each query keeps the module legible and lets the user expand only the query of interest.

# Changes

- Replaced `CreateQueryHeading` and the `.query-heading` style with a `query-fields` container created via `CreateContainer`.
- Styled query summaries as bold, uppercase, 13px; raised module summaries to 17px so the module remains the most prominent grouping.
- Module disabling now reaches requirement sections nested within query containers, since a query has no toggle of its own.
- Updated page tests for the new container, disabling selector, and summary styles.

# Compatibility

- Visual change only; form fields and submitted values are unchanged.
