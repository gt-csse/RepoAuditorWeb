---
type: Change
title: Insufficient PAT errors name the permission the token is missing
description: The error reported when a Personal Access Token cannot see a restricted repository value now states which fine-grained permission the token needs.
tags: [github, personal-access-token, restricted-value, error-messages]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-15T15:22:49Z }
resource: src/RepoAuditorWeb/lib/plugins/github_impl/standard_requirements/restricted_value.py
---

# Summary

When a Personal Access Token (PAT) is provided but does not grant enough access to see a restricted repository value, `GetRestrictedValue` now appends guidance to the error context: the token must be created by a GitHub user with access to the repository and must have the required fine-grained permission (`Contents: Read and write` for push, `Administration: Read` for admin).

# Motivation

The previous context stated only that the token lacked push or admin access. GitHub's fine-grained tokens are scoped to explicit permissions, so a token owned by a user with the correct repository role can still fail; naming the specific permission and the ownership requirement lets the user correct the token directly from the error.

# Changes

- `GetRestrictedValue` error context expands "Personal Access Token" to "Personal Access Token (PAT)" and adds a paragraph naming the required fine-grained permission from `_FINE_GRAINED_PERMISSIONS`.
- Updated the expected contexts in the restricted value tests and in the tests for every requirement built on `GetRestrictedValue` (merge, auto-merge, rebase, squash, branch update, head branch deletion, commit message, Dependabot, secret protection, push protection, and classic branch protection).

# Compatibility

- Error context text for insufficient-PAT results changed; consumers matching the exact string must be updated.
- Result values and resolutions are unchanged.
