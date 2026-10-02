---
type: Change
title: Added a CONTRIBUTING requirement to the CommunityStandards module
description: Added ContributingRequirement to the CommunityStandards query and aligned file search order with GitHub's.
tags: [community-standards, plugins, github, requirement]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T15:33:25Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/contributing.py
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
  - id: github-contributor-guidelines
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors
    title: Setting guidelines for repository contributors
    author: GitHub
---

# Summary

Added `ContributingRequirement`, which validates that a `CONTRIBUTING` file exists in the `.github`, root, or `docs` directory using GitHub's detection rules (case-insensitive, any extension). The requirement is registered in `CommunityStandardsQuery` after `CodeOfConduct`.

# Motivation

CONTRIBUTING is one of the files GitHub reports in a repository's community profile and links to when contributors open issues or pull requests. This is the third community standards file implemented as a thin `FileExistsRequirement` subclass.

# Changes

- New `ContributingRequirement` named `Contributing`, with a resolution that links to example CONTRIBUTING files referenced by GitHub and a rationale describing when to override the default.
- `Readme`, `CodeOfConduct`, and `Contributing` now search `.github`, `.`, then `docs`, matching the order GitHub searches. Error messages list directories in this order.
- The `CodeOfConduct` resolution now lists the templates GitHub offers when adding the file through its web interface.
- Tests cover detection variants, the missing-file error, and the end-to-end query with all three files present.
