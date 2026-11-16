---
type: Change
title: Console colors in the web output log
description: The web output log colors what the console colors (errors, warnings, and results such as the value in "DONE! (<result>, <time>)") using the page's own error, warning, and success colors.
tags: [feature, web, ui, output]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-16T16:02:03Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The web output log is now colored where the console colors it. Red, yellow, and green are rendered bold in the page's error, warning, and success colors, which adapt to light and dark themes; any other color code (e.g. inverse video) is dropped and its text shown plainly.

# Motivation

The page previously found `ERROR` and `WARNING` labels with a pattern, which colored only those labels and duplicated the console's rules. Receiving the console's own color codes colors everything the console colors, such as a failing result in `DONE! (-1, ...)`, without reproducing its rules in the page.

# Changes

- The output stream declares that it supports colors, so `DoneManager` writes the same ANSI codes the console displays. The stream still reports that it is not a terminal so that `DoneManager` does not move the cursor.
- The page splits each line on ANSI color codes and maps codes 31, 32, and 33 to the `error`, `success`, and `warning` classes.
- The unfinished last line is kept as received text so that its codes survive redraws; a code split across chunks is hidden until the next chunk completes it.
- Updated the page, server, and stream tests.

# Compatibility

- No changes to the command line, the console experience, or the json experience or its schema.
- Only the web output stream carries color codes; the rendered log and copied text contain none.
