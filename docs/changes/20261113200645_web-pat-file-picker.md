---
type: Change
title: File picker for the web PAT field
description: The web form's PAT field has a folder button (labeled Browse...) that opens the native file dialog in the app window and fills in the chosen file's path.
tags: [feature, pat, web, ui]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-13T20:06:45Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The PAT field in the web form now has a folder button, labeled `Browse...` for tooltips and screen readers, beside its text input. Clicking it opens the operating system's file dialog and places the chosen file's full path in the field; cancelling leaves the field unchanged. The button is shown only in the app window, so the page opened in a regular browser displays the text input alone.

# Motivation

The PAT is accepted only as the path to a file, so users had to type the full path to their token file. A browser's `<input type="file">` does not reveal the chosen file's path, which the server needs to read the token, so the dialog is opened by the app window instead.

# Changes

- `FieldType.FilePath` is selected for parameters typed `Path`. The common `pat` parameter is typed `Path | None` to select it; the submitted value remains a string, matching what the command line provides, so every experience receives the same type.
- The window exposes a `SelectFile` function to the page through pywebview. It opens the native open dialog and returns the first chosen path, or `None` when cancelled.
- The page wraps a file path field's input with a folder button that calls `SelectFile`. The button stays hidden until pywebview injects its API, whether that happens before or after the form is built.
- Added tests for the field type, the exposed function, and the page script.

# Compatibility

- No changes to the command line, the console experience, or the json experience or its schema.
- Only `SelectFile` is exposed to the page; it returns a path the user chose and does not read the file.
