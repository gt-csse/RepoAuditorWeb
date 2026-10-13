---
type: Change
title: Removed the TUI experience
description: The textual-based tui experience, its tests, and the textual dependency are removed; web, console, and json remain.
tags: [removal, tui, cli]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T14:30:44Z }
resource: src/RepoAuditorWeb/__main__.py
---

# Summary

The `tui` experience is removed. `--experience` accepts `web`, `console`, and `json`.

# Motivation

The TUI experience is not production quality. Removing it avoids shipping it and eliminates the cost of keeping it in sync with the other experiences.

# Changes

- Deleted `tui_experience.py`, the `tui_experience_impl` package, and their tests.
- Removed `Experience.Tui` and its dispatch from `EntryPoint`, along with its entry point test.
- Removed the `textual` dependency.
- README no longer lists the `tui` experience or references it for `--execute` and the `Common` section.

# Compatibility

- `--experience tui` is no longer accepted.
