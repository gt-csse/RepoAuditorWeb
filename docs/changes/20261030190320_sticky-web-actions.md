---
type: Change
title: Web form Execute and Reset buttons stay in view while scrolling
description: The web form's action bar sticks to the bottom of the window while the form is scrolled, so Execute and Reset remain reachable without scrolling to the end of the form.
tags: [web, ui, form, sticky, css]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-30T19:03:20Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The `.actions` bar holding the Execute and Reset buttons is now `position: sticky` at the bottom of the window, with a background and top border so it reads as a footer over scrolled form content. It is contained by the form's section, so once the form scrolls past, the bar is left behind instead of covering the output and results below it.

# Motivation

The form can span several screens, so running or resetting an audit previously required scrolling to its end. Keeping the buttons in view mirrors the sticky header at the top of the page.

# Changes

- `.actions` is sticky at `bottom: 0` with `z-index: 1`, a full-bleed background, padding, and a top border.
- `main` defines its padding as `--gutter`, which the action bar reuses to extend to the edges of `main`.
- The sticky header's `z-index` is raised from `1` to `2` so the action bar passes beneath it as it scrolls out of view.
- Added `test_ActionsStayInViewWhileTheFormIsScrolled` to the page tests.

# Compatibility

- Visual-only change to the web page; no API or result changes.
