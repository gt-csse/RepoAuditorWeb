---
type: Change
title: Web form scrolls to the output when executing
description: Executing the web form scrolls the output section to just beneath the sticky header, and the output and results reserve a window's height so the results arrive in view, directly beneath the output.
tags: [web, ui, form, scroll, css]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-11T17:20:50Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

Clicking Execute scrolls the output section to just beneath the sticky header, smoothly unless the system prefers reduced motion. While the output is shown, the output and results sections together reserve a window's height, so the output can reach the top of the window and the results arrive in view, directly beneath it. The results arriving do not scroll the page.

# Motivation

The form can span several screens, so a run would otherwise begin below the bottom of the window. The output log starts empty and is last on the page, so without the reserved height the page could only scroll it to the bottom of the window. Scrolling again when the results arrive would pull the page away from the output being read.

# Changes

- Added `ScrollToOutput`, called by `Execute` once the output section is shown; it honors `prefers-reduced-motion`.
- Wrapped the output and results sections in `#run`, which has `min-height: calc(100vh - var(--header-clearance))` while `#output-section` is shown.
- `#output-section` has `scroll-margin-top: var(--header-clearance)` (64px) so it stops beneath the header when scrolled to.
- Added `test_ExecuteScrollsToTheOutput` to the page tests.

# Compatibility

- Web page change only; no API, result, or CLI changes.
