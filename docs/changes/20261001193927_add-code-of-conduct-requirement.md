---
type: Change
title: Added a CODE_OF_CONDUCT requirement to the CommunityStandards module
description: Added CodeOfConductRequirement to the CommunityStandards query and renamed the README requirement to Readme.
tags: [community-standards, plugins, github, requirement]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-01T19:39:27Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/code_of_conduct.py
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
---

# Summary

Added `CodeOfConductRequirement`, which validates that a `CODE_OF_CONDUCT` file exists in the root, `docs`, or `.github` directory using GitHub's detection rules (case-insensitive, any extension). The requirement is registered in `CommunityStandardsQuery` after `Readme`.

# Motivation

CODE_OF_CONDUCT is one of the files GitHub reports in a repository's community profile. This is the second community standards file implemented as a thin `FileExistsRequirement` subclass, following the plan established when the CommunityStandards module was introduced.

# Changes

- New `CodeOfConductRequirement` named `CodeOfConduct`.
- `ReadmeRequirement` was renamed from `README` to `Readme` so requirement names consistently use PascalCase. Configuration and arguments that referenced `README` must now use `Readme`.
- Tests cover detection variants, the missing-file error, and the end-to-end query with both files present.
