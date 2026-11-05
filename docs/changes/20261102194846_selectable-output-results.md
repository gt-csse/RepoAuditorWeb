---
type: Change
title: Web output and results text is selectable for copying
description: The web page's output log and results opt back in to text selection, which pywebview disables across the page by default, so errors and resolutions can be copied.
tags: [web, ui, output, results, css, copy]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-02T19:48:46Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The `#output` log and `#results` container now set `user-select: text` and `cursor: auto`, overriding the `body { user-select: none; cursor: default; }` rule that pywebview injects. Text in those regions can be highlighted and copied, while the rest of the window stays unselectable.

# Motivation

No text in the app window could be highlighted or copied, so an error could not be pasted into a search and a resolution's steps could not be copied. Enabling selection only for the output and results, rather than passing `text_select=True` to `webview.create_window`, keeps dragging across the form's switches from highlighting their labels.

# Changes

- Added a `#output, #results` rule to the page's styles that sets `-webkit-user-select: text`, `user-select: text`, and `cursor: auto`.
- The output log no longer scrolls to new output while text in it is selected, since scrolling would move the selected text away before it is copied, or extend a selection in progress.
- Added `test_OutputAndResultsAreSelectable` and `test_OutputDoesNotScrollWhileSelecting` to the page tests.

# Compatibility

- Web page change only; no API or result changes. The output log now pauses auto-scrolling while text in it is selected.
