---
type: Change
title: Moved ContributingRequirement back to the community standards requirements
description: ContributingRequirement returns from RepoAuditorWeb.lib.plugins.shared to community_standards_impl/requirements/contributing.py, alongside the other community standards file requirements.
tags: [refactor, plugins, shared, community-standards]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-08T13:29:28Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/contributing.py
---

# Summary

`ContributingRequirement` moves from `shared/contributing_requirement.py` back to `community_standards_impl/requirements/contributing.py`, partially reverting the shared component extraction. Its implementation is unchanged.

# Motivation

The shared package holds generic building blocks for custom modules. `ContributingRequirement` is a concrete requirement used only by `CommunityStandardsQuery`, and its sibling requirements (code of conduct, license, security, and others) remain in `community_standards_impl/requirements`. Custom modules that need a similar check can derive from `FileExistsRequirement`.

# Changes

- `shared/contributing_requirement.py` renamed to `community_standards_impl/requirements/contributing.py`.
- `CommunityStandardsQuery` imports `ContributingRequirement` from the new location.
- `tests/lib/plugins/shared/contributing_requirement_test.py` renamed to `tests/lib/plugins/community_standards_impl/requirements/contributing_test.py` with the updated import.
- `docs/custom_modules.md` no longer lists `ContributingRequirement` as a shared component.

# Compatibility

Custom modules importing `ContributingRequirement` from `RepoAuditorWeb.lib.plugins.shared.contributing_requirement` must import it from `RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.contributing`.
