---
type: Change
title: The web form's section is named Options and the page's section headings are larger
description: The web form's section heading reads Options instead of Arguments, and section headings are larger than the query headings that share their style.
tags: [web, form, headings, text]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-29T18:03:38Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

The web form's section heading now reads `Options` instead of `Arguments`, and the page's section headings are larger (15px, 0.08em letter spacing) than the uppercase query headings nested within them.

# Motivation

`Arguments` reflects the command line rather than what the form is to a web user. The section headings shared the size of the query headings inside them, so the page's structure did not read from the outside in.

# Changes

- `CreatePage` renders `<h2>Options</h2>` for the form's section.
- `section > h2` font size increased from 13px to 15px and letter spacing from 0.06em to 0.08em.
- Added `test_SectionHeadingsLeadThePage` covering the heading text and size.

# Compatibility

- Visual and text change only; the section's `id` remains `arguments`, so selectors are unaffected.
