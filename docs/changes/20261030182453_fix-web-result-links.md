---
type: Change
title: Links open in the browser from the macOS app window
description: Clicked web links are marked to open elsewhere and followed natively, so the macOS app window hands them to the default browser as the Windows window does.
tags: [web, links, macos]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-30T18:24:53Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The page's link click handler no longer intercepts `http`/`https` links with `window.open`. It instead sets `target="_blank"` and `rel="noopener"` on the clicked link and lets the click be followed, so clicking a web link from the macOS app window opens it in the default browser.

# Motivation

The macOS app window drops the page's calls to `window.open` and only hands a clicked link that opens elsewhere to the browser, so links did nothing there. The Windows app window hands both to the browser, so following the link natively behaves the same on both platforms.

# Changes

- The click handler marks clicked `http`/`https` links to open elsewhere instead of calling `preventDefault` and `window.open`.
- Added a page test that matches the whole click handler, so a reintroduced `preventDefault` or `window.open` fails it.

# Compatibility

- No markup or API changes; links on every platform open in the browser or a new tab as before, and now also from the macOS app window.
