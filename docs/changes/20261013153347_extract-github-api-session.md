---
type: Change
title: Extracted a reusable GitHub API session from GitHubSession
description: GitHubSession now derives from a GitHubApiSession base class and uses a GetApiBaseUrl helper, so API calls not tied to a single repository can reuse its configuration.
tags: [github, refactor]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T15:33:47Z }
resource: src/RepoAuditorWeb/lib/plugins/shared/github_session.py
---

# Summary

The retry, header, PAT, timeout, and relative-request behavior of `GitHubSession` moved into a new public `GitHubApiSession` base class, and the mapping from a GitHub server to its REST API base url moved into a new public `GetApiBaseUrl` function. `GitHubSession` derives from the base class and only parses and validates the repository url.

# Motivation

A follow-up change audits every repository owned by a GitHub user or organization, which requires API calls (listing an owner's repositories) that are not relative to a single repository. Extracting the shared session configuration and API url mapping lets that work reuse them rather than duplicate them.

# Changes

- Added `GetApiBaseUrl(scheme, netloc)`, which returns `https://api.github.com` for public GitHub and `<scheme>://<host>/api/v3` for GitHub Enterprise.
- Added `GitHubApiSession(api_url, github_pat)` with the retry adapter, headers, PAT authorization, default timeout, and requests relative to `api_url`. It removes trailing slashes from the url path, rejects urls without an http(s) scheme and host or with params, a query, or a fragment, and upgrades the url to https whenever a PAT is present, so the PAT is never sent over an unencrypted connection regardless of the caller.
- `GitHubSession` derives from `GitHubApiSession`; its constructor signature and attributes are unchanged.
- Listed `GitHubApiSession` and `GetApiBaseUrl` in the shared building blocks table of `docs/custom_modules.md`.
- Added tests for the helper, the base class, and `GitHubSession` url validation.

# Compatibility

- `GitHubSession` rejects urls whose scheme is not `http` or `https` with its existing "is not a valid GitHub repository URL" error. Previously, urls such as `file://github.com/<owner>/<repository>` produced a session that queried GitHub, and urls such as `file://<host>/<owner>/<repository>` without a PAT produced a session that failed on its first request.
- Behavior for `http` and `https` repository urls is unchanged.
