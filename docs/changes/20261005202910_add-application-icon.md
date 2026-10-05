---
type: Change
title: Added an application icon to the web experience
description: The webview window, browser tab, and page header display a RepoAuditor icon.
tags: [web, ui]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T20:29:10Z }
resource: src/RepoAuditorWeb/web_experience_impl/server.py
---

# Summary

The web experience displays a RepoAuditor icon in the webview window, the page's favicon, and the page header.

# Motivation

Without an icon, the window and taskbar entry use the generic webview icon, which makes the application hard to identify among other open windows.

# Changes

- Added `icon.svg` (page favicon and header) and `icon.ico` (window icon) to `web_experience_impl`.
- The server serves the SVG at `/icon.svg`.
- `ExecuteExperience` passes the ICO file to `webview.start`, because ICO is the only format the Windows backend loads.
- The page header displays the icon to the left of the title.
- Added tests for the `/icon.svg` endpoint, the favicon and header markup, and the window icon path.
