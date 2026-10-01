---
type: Change
title: Added the CommunityStandards module with a README requirement
description: Introduced a clone-based CommunityStandards module that validates GitHub community standards files, starting with README.
tags: [community-standards, plugins, github, query]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-01T19:15:31Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
---

# Summary

Added a `CommunityStandards` module that shallow-clones the target repository and validates files GitHub treats as community standards. The first requirement, `README`, checks the root, `docs`, and `.github` directories using GitHub's detection rules (case-insensitive, any extension). Repository arguments (`--url`, `--pat`, `--branch`) were extracted from the GitHub module so both modules share them.

# Motivation

Establishes the infrastructure for file-based checks: a reusable `FileExistsRequirement` and a query lifecycle that can clean up resources such as a cloned working tree. Additional community standards files (LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, etc.) are expected to follow as thin subclasses of `FileExistsRequirement`.

# Changes

- `Query.CleanupQueryData` is a new abstract method; `Execute` invokes it after a query's requirements are evaluated, even on failure. Existing GitHub queries implement it as a no-op.
- `CommunityStandardsQuery` clones into a `TemporaryDirectory` via GitPython (new dependency `gitpython`), imported lazily so the dependency is only loaded when the module runs.
- PATs are embedded in the clone URL; clone errors redact the PAT and do not chain the original exception, preventing the PAT from appearing in tracebacks.
- `FileExistsRequirement` exposes a `prohibit` parameter to invert the check.
- `repository_arguments.py` provides `GetRepositoryParameters` and `ResolveRepositoryArguments`, shared by the GitHub and CommunityStandards modules. Blank or whitespace-only PATs are now rejected.
- The entry point gained common `--url`, `--pat`, and `--branch` options (with `REPO_AUDITOR_WEB_GITHUB_*` environment variables) that are applied to every module declaring a parameter of the same name, unless a module-specific value is provided.

# Known interim state

- `CommunityStandardsModule` uses `requires_explicit_include=False` (marked `TODO: True`) so it runs by default during development; `GitHubModule` now requires explicit inclusion.
