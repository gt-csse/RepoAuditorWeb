---
type: Change
title: Added a PULL_REQUEST_TEMPLATE requirement to the CommunityStandards module
description: Added PullRequestTemplateRequirement to the CommunityStandards query, and hardened file detection and result rendering against untrusted repository content.
tags: [community-standards, plugins, github, requirement, pull-request-template, security]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T17:23:12Z }
resource: src/RepoAuditorWeb/lib/plugins/community_standards_impl/requirements/pull_request_template.py
sources:
  - id: github-community-profile
    resource: https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories
    title: About community profiles for public repositories
    author: GitHub
  - id: github-pull-request-template
    resource: https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository
    title: Creating a pull request template for your repository
    author: GitHub
---

# Summary

Added `PullRequestTemplateRequirement`, which validates that a `PULL_REQUEST_TEMPLATE` file (any extension, case-insensitive) exists in `.github`, the repository root, or `docs`. The requirement is registered in `CommunityStandardsQuery` after `IssueTemplate`. File detection now ignores symlinks that escape the repository, and rendered results escape raw HTML.

# Motivation

A pull request template is one of the items GitHub reports in a repository's community profile; it prompts authors for the details reviewers need. The audited repository is untrusted: following symlinks out of it would reveal whether paths exist on the host, and filenames embedded in result context could inject markup into the results page.

# Changes

- New `PullRequestTemplateRequirement` named `PullRequestTemplate`, built on `FileExistsRequirement` and searching `.github`, `.`, and `docs`.
- The rationale notes override cases: organization-level default templates in a `.github` repository, repositories that do not accept pull requests, and templates stored in a `PULL_REQUEST_TEMPLATE` directory, which this requirement does not detect.
- `FileExistsRequirement` resolves the repository directory and skips searched directories and matched items whose resolved paths fall outside it.
- `results_html` configures `MarkdownIt` with `html: False` so raw HTML in content is escaped.
- Tests cover detection variants, rejected locations, symlinks within and outside the repository, HTML escaping, and the end-to-end query with all six items present.
