---
type: Change
title: Web output log highlights error and warning labels
description: The web output log colors the ERROR and WARNING labels that DoneManager writes, matching how the console colors them in a terminal.
tags: [web, ui, output, log, css]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-02T11:41:02Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

Lines in the web output log that begin with `ERROR:` or `WARNING:` (after any indentation) have their label wrapped in a span colored with the page's `--error` or `--warning` token and set in a heavier weight. The message that follows the label is left uncolored.

# Motivation

A module's failure is reported only in the log, so errors and warnings were easy to miss among the surrounding progress lines. In a terminal, DoneManager already colors these labels, but `StreamSink.isatty()` returns `False` so that no escape sequences reach the browser, which left the web log uncolored. Only the label is colored because a message may span several lines and reads better uncolored.

# Changes

- Added `AppendOutput`, which appends each chunk's complete lines and redraws only the unfinished last line, held in its own span, since a chunk may end mid-line and split a label. Redrawing the whole log instead would slow a long run with every chunk.
- `Reset` also clears the unfinished line.
- Added `#output .error` and `#output .warning` styles.
- Added `test_OutputHighlightsErrorAndWarningLabels` and `test_OutputAppendsCompleteLinesAndRedrawsOnlyTheTail` to the page tests.

# Compatibility

- Visual-only change to the web page; the streamed output and the console are unchanged.
