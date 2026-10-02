---
type: Change
title: Added a LICENSE requirement to the CommunityStandards module
description: Added LicenseRequirement to the CommunityStandards query to validate that a LICENSE file exists in the repository root.
tags: [community-standards, plugins, github, requirement, license]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T16:08:00Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/license.py
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
  - id: github-licensing
    resource: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
    title: Licensing a repository
    author: GitHub
  - id: choosealicense
    resource: https://choosealicense.com/
    title: Choose an open source license
    author: GitHub
---

# Summary

Added `LicenseRequirement`, which validates that a `LICENSE` file (any extension, case-insensitive) exists in the root of the repository. The requirement is registered in `CommunityStandardsQuery` after `Contributing`.

# Motivation

A license is one of the items GitHub reports in a repository's community profile. Without one, default copyright applies and others have no legal permission to use, modify, or distribute the code. GitHub only detects licenses in the repository root, so detection is limited to that single location.

# Changes

- New `LicenseRequirement` named `License`, built on `FileExistsRequirement` and searching only `.`.
- The resolution links to choosealicense.com and the MIT, Apache 2.0, and GPLv3 templates GitHub offers.
- The rationale notes override cases: proprietary repositories governed by external agreements, and license files GitHub recognizes but this requirement does not (`COPYING`, `LICENCE`, `UNLICENSE`, `LICENSE-MIT`, `LICENSES/`). It also notes that license contents are not validated.
- Tests cover detection variants in the root, rejected locations (`.github`, `docs`), and the end-to-end query with all five items present.
