---
type: Change
title: Documented the PAT permissions required by each module
description: The README and PAT-related resolution messages identify the fine-grained token permissions and classic token scope needed to evaluate restricted requirements.
tags: [docs, github, pat, security]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-06T13:08:54Z }
resource: README.md
---

# Summary

The README gains a `PAT Permissions` section that maps each module's restricted data to the fine-grained token permission and repository role GitHub requires. Resolution text produced when a PAT is missing or insufficient now names the specific fine-grained permission and the classic `repo` scope.

# Motivation

Fine-grained tokens are limited to explicitly granted permissions, so holding the necessary repository role is not sufficient for GitHub to report restricted settings. Previous messages only stated the required access level, leaving users to discover which token permission was missing by trial and error.

# Changes

- `README.md` links the `--pat` option to GitHub's token documentation and adds a `PAT Permissions` table covering `CommunityStandards`, `ScientificSoftware`, and `GitHub` data.
- `restricted_value.py` maps `AccessLevel.Push` to `Contents: Read and write` and `AccessLevel.Admin` to `Administration: Read`, and includes the mapped permission and the classic `repo` scope in both the no-PAT and insufficient-PAT resolutions.
- `cloned_repository_query.py` notes that cloning a private repository requires `Contents: Read` on a fine-grained PAT or the `repo` scope on a classic PAT.
- Tests updated to assert the revised resolution and error text.
