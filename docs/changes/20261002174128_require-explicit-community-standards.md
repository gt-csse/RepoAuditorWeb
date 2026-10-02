---
type: Change
title: Required explicit inclusion of the CommunityStandards module
description: Changed the CommunityStandards module to run only when explicitly included, replacing its skip parameter with an include parameter.
tags: [community-standards, plugins, module, configuration]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T17:41:28Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/module.py
---

# Summary

`CommunityStandardsModule` now passes `requires_explicit_include=True`, resolving the `TODO` left in place while the module's requirements were under development. The module no longer runs by default; users opt in via its `include` parameter, which replaces the previous `skip` parameter.

# Motivation

The module was left enabled by default while its requirements were being built out. With the requirement set complete, it is aligned with the other repository-specific modules (`GitHub`, `ScientificSoftware`), which also require explicit inclusion so that runs do not perform repository checks the user did not request.

# Changes

- `requires_explicit_include` changed from `False` to `True` in `CommunityStandardsModule`.
- The module's generated parameter changes from `skip` to `include`; existing invocations that relied on the module running by default must now include it explicitly.
- Tests no longer pass `--CommunityStandards-skip` to avoid network calls, since no module runs by default; module and parameter expectations are updated to `include`.
