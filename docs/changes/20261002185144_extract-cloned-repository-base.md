---
type: Change
title: Extracted cloned-repository module and query base classes into a shared package
description: Moved repository cloning, repository arguments, and the file-exists requirement out of CommunityStandards and GitHub into a reusable plugins/shared package.
tags: [community-standards, github, plugins, refactor]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T18:51:44Z }
resource: src/RepoAuditorWeb/lib/plugins/shared
---

# Summary

Repository-cloning logic previously embedded in `CommunityStandardsModule` and `CommunityStandardsQuery` now lives in `ClonedRepositoryModule` and `ClonedRepositoryQuery` within the new `plugins/shared` package. `CommunityStandardsModule` and `CommunityStandardsQuery` derive from these base classes; behavior is unchanged.

# Motivation

Cloning the target repository, resolving `url`/`branch`/`pat` arguments, and checking for file existence are not specific to Community Standards. Moving them to a shared package lets future plugins that inspect repository contents reuse the same cloning, PAT redaction, and cleanup behavior instead of duplicating it.

# Changes

- Added `shared/cloned_repository_module.py` (`ClonedRepositoryModule`): supplies repository parameters, resolves module data, and always sets `requires_explicit_include=True` because a url is required.
- Added `shared/cloned_repository_query.py` (`ClonedRepositoryQuery`): clones the repository into a temporary `repo_dir`, redacts the PAT from clone errors, and cleans up the directory.
- Moved `github_impl/repository_arguments.py` to `shared/repository_arguments.py`; `GitHubModule` imports updated.
- Moved `community_standards_impl/requirements/impl/file_exists_requirement.py` to `shared/file_exists_requirement.py`; all Community Standards requirements updated.
- Tests for cloning and argument handling moved from the Community Standards test files into `tests/lib/plugins/shared/`.
