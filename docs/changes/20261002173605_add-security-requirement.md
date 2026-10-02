---
type: Change
title: Added a SECURITY requirement to the CommunityStandards module
description: Added SecurityRequirement to the CommunityStandards query to validate that a SECURITY file exists in the `.github` directory, the repository root, or the `docs` directory.
tags: [community-standards, plugins, github, requirement, security]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T17:36:05Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/security.py
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
  - id: github-security-policy
    resource: https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository
    title: Adding a security policy to your repository
    author: GitHub
---

# Summary

Added `SecurityRequirement`, which validates that a `SECURITY` file (any extension, case-insensitive) exists in one of the locations GitHub searches: `.github`, the repository root, or `docs`. The requirement is registered in `CommunityStandardsQuery` after `License`.

# Motivation

A security policy is one of the items GitHub reports in a repository's community profile. Without documented reporting instructions, reporters may disclose vulnerabilities in public issues, exposing users before a fix is available. A policy also communicates which versions receive security fixes.

# Changes

- New `SecurityRequirement` named `Security`, built on `FileExistsRequirement` and searching `.github`, `.`, and `docs`.
- The resolution describes the expected content (supported versions, private reporting channel, response timeline) and links to GitHub's security policy documentation.
- The rationale notes override cases: organization-level default `SECURITY` files in the `.github` repository, which this requirement cannot detect, and repositories with no audience for a disclosure process (personal, mirrored, or archived).
- Tests cover detection variants in each searched location, rejected locations (`src`, nested `.github/SECURITY/`), and the end-to-end query with all seven items present.
