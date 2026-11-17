---
type: Change
title: Sort web results by kind or run order
description: The web results can be sorted by kind, leading with errors and then warnings, or shown in the order they ran.
tags: [feature, web, ui, results]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-17T17:26:19Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

A "Sort by" control beside the Results heading switches between "Run order" (the default) and "Kind". Sorting by kind lists errors first, then warnings, success, does not apply, and skipped; requirements of the same kind keep the order they ran.

# Motivation

Results arrive in the order they were evaluated, which interleaves errors with warnings and other results. Sorting by kind puts what needs attention first for triage, while run order still matches the output log, the console, and JSON.

# Changes

- The page's configuration carries the result values ordered from errors to skipped, drawn from `RESULT_VALUE_NAMES` so that a new result value cannot be left unsorted.
- The page records the order in which requirements arrive and reorders the existing elements when the order changes, restoring the run order when it is selected again. A new run is sorted on arrival using the selected order.
- The control sits beside the heading and is hidden when there is nothing to sort: a failed run or one with no requirements to report.
- Updated the page tests.

# Compatibility

- No changes to the command line, the server, the rendered results HTML, the console experience, or the json experience or its schema.
