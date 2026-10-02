---
type: Change
title: Added an ISSUE_TEMPLATE requirement to the CommunityStandards module
description: Added IssueTemplateRequirement to the CommunityStandards query and allowed FileExistsRequirement to detect directories.
tags: [community-standards, plugins, github, requirement]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T15:53:50Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/issue_template.py
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
  - id: github-issue-templates
    resource: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository
    title: Configuring issue templates for your repository
    author: GitHub
  - id: github-issue-forms
    resource: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms
    title: Syntax for issue forms
    author: GitHub
---

# Summary

Added `IssueTemplateRequirement`, which validates that an `ISSUE_TEMPLATE` directory exists in the `.github` directory (case-insensitive). The requirement is registered in `CommunityStandardsQuery` after `Contributing`.

# Motivation

Issue templates are one of the items GitHub reports in a repository's community profile. Unlike the other community standards files, GitHub only recognizes issue templates as files within a `.github/ISSUE_TEMPLATE` directory; the legacy single-file template and locations outside of `.github` are no longer supported, so detection must target a directory in a single location.

# Changes

- `FileExistsRequirement` accepts an `is_directory` keyword; when set, only directories whose names match exactly (case-insensitive, no extension stripping) are detected. The default behavior is unchanged.
- `FileExistsRequirement` error messages read "was not found in the `<dir>` directory" when only one directory is searched.
- New `IssueTemplateRequirement` named `IssueTemplate`, with a resolution that links to GitHub's Markdown issue templates and YAML issue forms, and a rationale noting that organization-level default templates and template contents are not inspected.
- Tests cover directory detection and single-directory messages in the base class, detection variants and rejected legacy locations, and the end-to-end query with all four items present.
