---
type: Change
title: Expanded README and CODE_OF_CONDUCT requirement rationales
description: The README and CODE_OF_CONDUCT requirements now describe their default behavior, the reasons for it, and the reasons to override it.
tags: [requirement, rationale, plugins, community-standards]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T10:47:02Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements
---

# Summary

The rationales for `ReadmeRequirement` and `CodeOfConductRequirement` were single paragraphs describing what the file is. They now state the default behavior and list "Reasons for this Default" and "Reasons to Override this Default".

# Motivation

Requirement defaults can be overridden through configuration, so a rationale must help users decide whether the default applies to their repository. A description of the file alone did not provide the information needed to make that decision.

# Changes

- Rewrote the `ReadmeRequirement` rationale, including a note on GitHub's README resolution order (`.github`, root, `docs`).
- Rewrote the `CodeOfConductRequirement` rationale, including a note that organization-level `.github` defaults are not detected by this requirement.
- Updated the corresponding test expectations.
