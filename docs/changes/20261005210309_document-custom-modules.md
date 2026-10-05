---
type: Change
title: Documented how to create custom modules in separate packages
description: A new guide describes how to author, register, run, and test RepoAuditorWeb modules distributed in separate packages.
tags: [docs, plugins, modules]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T21:03:09Z }
resource: docs/custom_modules.md
---

# Summary

`docs/custom_modules.md` explains how to define custom modules in separate packages that `RepoAuditorWeb` discovers through `pluggy` entry points. The README and `DEVELOPMENT.md` link to the guide.

# Motivation

Modules are loaded from the `RepoAuditorWeb` entry point group, so teams can add organization-specific requirements without modifying this repository. That extension point was undocumented, leaving the module, query, and requirement contracts discoverable only by reading the source.

# Changes

- Added `docs/custom_modules.md`, covering the `Module`, `Query`, and `Requirement` concepts, the shared building blocks in `RepoAuditorWeb.lib.plugins.shared`, entry point registration, naming rules, running the audit, and testing requirements.
- Included two examples: a file-validation module assembled from `ClonedRepositoryModule`, `ClonedRepositoryQuery`, and `FileExistsRequirement`, and a module that queries the GitHub REST API for repository topics with a configurable requirement parameter.
- `README.md` references the guide from the `Overview` and the additional information table.
- `DEVELOPMENT.md` adds a `Custom Modules` section that links to the guide.
