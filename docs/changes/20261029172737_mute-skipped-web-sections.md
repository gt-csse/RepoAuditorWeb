---
type: Change
title: Web form mutes modules and requirements that do not run
description: Modules and requirements that are skipped are now visually muted in the web form, and a requirement's pill reports "skipped" when its module is skipped.
tags: [web, form, styling, pill, skipped]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-29T17:27:37Z }
resource: src/RepoAuditorWeb/web_experience_impl/page.py
---

# Summary

Disabled modules render with a transparent background and dashed border, and the names of disabled modules, their query sections, and disabled requirements use the `--skipped` color. A requirement's pill now reads "skipped" whenever its module is skipped, regardless of the requirement's own field, and refreshes when the module's disabling changes.

# Motivation

Whether a module or requirement runs could previously be read only from its pill, and a requirement inside a skipped module still claimed to be "included". Muting skipped containers makes their state apparent at a glance, and colors are muted instead of lowering opacity so the already-dimmed disabled controls are not dimmed twice.

# Changes

- Added `.module-fields.disabled` and `.requirement-fields.disabled` styles to `_STYLE`.
- `AddPill` takes the container's `details` element, treats an inherited `disabled` state as skipped, and refreshes on the `refresh-disabling` event.
- Added `test_PillFollowsTheModule` and `test_ContainersThatDoNotRunAreMuted`; removed the now-outdated `included` assertion from `test_PillTracksTheFieldThatGovernsTheContainer`.

# Compatibility

- Visual change to the web form only; audit behavior and results are unchanged.
