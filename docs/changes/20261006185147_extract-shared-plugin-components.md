---
type: Change
title: Extracted reusable plugin components into the shared package
description: GitHubSession, ContributingRequirement, RationaleRequirement, and repository path helpers move to RepoAuditorWeb.lib.plugins.shared so custom module packages can reuse them; GitHubSession gains a default timeout and retries.
tags: [refactor, plugins, shared, github, custom-modules]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T18:51:47Z }
resource: src/RepoAuditorWeb/lib/plugins/shared
---

# Summary

Components that were embedded in individual built-in modules now live in `RepoAuditorWeb.lib.plugins.shared`, alongside the existing shared base classes. `ClonedRepositoryModule` is renamed to `RepositoryModule` because it accepts any query, not only cloned-repository queries. `GitHubSession` applies a 30 second default timeout and retries transient failures.

# Motivation

Custom module packages could not reuse the GitHub API session, the CONTRIBUTING requirement, or the rationale and symlink-safety logic without importing from another module's implementation package or duplicating the code. Moving them to the shared package gives external modules a stable import location and removes duplicated rationale handling. `requests` waits indefinitely by default, so an unresponsive GitHub server could stall an audit, and rate limiting and server errors are often transient.

# Changes

- `shared/github_session.py` contains `GitHubSession`, moved from `github_impl/module.py`; it now mounts an `HTTPAdapter` retrying 3 times with backoff on 429/500/502/503/504 and sets a default request timeout of 30 seconds. All GitHub requirements and tests import it from the new location.
- `shared/rationale_requirement.py` adds `RationaleRequirement`, a `Requirement` whose `_CreateResult` attaches the rationale only when default values are in use. `FileExistsRequirement` derives from it.
- `shared/cloned_repository_query.py` adds `GetRepositoryDirectory` and `IsWithinRepository` so symlink-escape checks on untrusted repositories are shared rather than inlined.
- `shared/contributing_requirement.py` contains `ContributingRequirement`, moved from `community_standards_impl/requirements/contributing.py`.
- `shared/cloned_repository_module.py` is renamed to `shared/repository_module.py`, and `ClonedRepositoryModule` to `RepositoryModule`, which accepts `list[Query]`.
- `docs/custom_modules.md` lists the new shared components and uses `RepositoryModule` in its example.
- Tests added for `RationaleRequirement`, the repository path helpers, and the session timeout and retry configuration; existing tests moved or updated to follow the relocated code.

# Compatibility

Custom modules importing `ClonedRepositoryModule` from `shared.cloned_repository_module` or `GitHubSession` from `github_impl.module` must update their imports.
