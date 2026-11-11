---
type: Change
title: Links open in the browser from the macOS app window
description: Web links in the results are rendered to open elsewhere, so the macOS app window hands them to the default browser as the Windows window does.
tags: [web, links, macos]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-30T18:24:53Z }
resource: src/RepoAuditorWeb/web_experience_impl/results_html.py
---

# Summary

The results render `http`/`https` links with `target="_blank"` and `rel="noopener"`, and the page no longer intercepts their clicks with `window.open`, so clicking a web link from the macOS app window opens it in the default browser.

# Motivation

The macOS app window drops the page's calls to `window.open` and only hands a clicked link that opens elsewhere to the browser, so links did nothing there. The Windows app window hands both to the browser, so following the link natively behaves the same on both platforms.

# Changes

- Rendered `http`/`https` result links carry `target="_blank"` and `rel="noopener"`.
- The page's click handler only hides the link status, sharing the `mouseout` handler, instead of calling `preventDefault` and `window.open`.
- Results tests check the rendered anchors, and a page test checks that `window.open` is no longer used.

# Compatibility

- No API changes; links on every platform open in the browser or a new tab as before, and now also from the macOS app window.
