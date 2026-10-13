---
type: Change
title: Added wildcard urls to audit every repository of an owner or directory
description: A '--url' ending with '/*' audits every repository of a GitHub user or organization, or every git repository in a local directory, running the selected experience once per repository.
tags: [cli, github, json, multi-repository]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T19:01:43Z }
resource: src/RepoAuditorWeb/impl/repositories.py
---

# Summary

`--url` accepts a wildcard as its final path segment (`https://github.com/<owner>/*` or `file:///<directory>/*`). The entry point resolves the wildcard into a sorted list of repository urls and runs the selected experience once per repository under an `Auditing '<url>' (i of N)...` heading; a failure in one repository does not stop the others. The json document now contains an entry per repository and its schema version is 2.

# Motivation

Auditing an organization or a directory of clones previously required invoking the tool once per repository and merging the results by hand. Expanding the wildcard in the tool lets a single run cover every repository and produce a single document. The change builds on `GitHubApiSession` and `GetApiBaseUrl`, which were extracted from `GitHubSession` for this purpose.

# Changes

- Added `impl/repositories.py` with `ResolveRepositories` and `DisableModulesWithoutUrl`.
  - GitHub wildcards list `/orgs/<owner>/repos` for organizations, `/user/repos` when the PAT belongs to the owner (so private repositories are included), and `/users/<owner>/repos` otherwise, paging 100 at a time. The owner is validated with `NAME_REGEX` because it is placed in API paths.
  - Archived and forked repositories are excluded unless `--include-archived` or `--include-forked` is provided; these options are rejected without a GitHub wildcard url.
  - A warning is displayed when no PAT is provided, as GitHub then limits requests to 60 per hour and lists only public repositories.
  - Local wildcards include non-hidden subdirectories containing `.git` (directory or file), resolved so a repository reachable through a symlink is audited once. Remote `file://` hosts are rejected.
  - Partial wildcards, wildcards outside the final segment, and wildcard urls with params, a query, or a fragment are rejected. A public GitHub url naming only an owner is rejected with a suggestion to append `/*`.
  - Modules that do not accept a url run only with the first repository, as their results do not vary by repository.
- `__main__.py` iterates the resolved repositories, resolves a new port per repository (a previous server may still hold its port while shutting down), and warns that the `web` experience opens a window per repository unless `--execute` is provided.
- The json experience returns its entry instead of writing the document; `WriteDocument` writes `{schema_version, error, repositories}` once, however the run ends (including interruption). Each entry contains the module and common arguments, an `error`, a `summary`, and `results`. The PAT is redacted as `***`.
- `ResolvePat` was extracted from `ResolveRepositoryArguments` so wildcard enumeration reads a PAT file the same way modules do. `ResolveRepositoryArguments` rejects urls that still contain a wildcard, which can only be entered where wildcards are not expanded (such as the web form).
- `NAME_REGEX` in `github_session.py` became public for reuse.
- The web experience stops its server even when the window fails, so the next repository's server can start.
- Documented the feature and the new json schema in `README.md`, and added tests.

# Compatibility

- The json document's `schema_version` changed from 1 to 2. The top-level `summary` and `results` moved into each element of `repositories`, and top-level `error` was added. Consumers of version 1 must be updated.
- A url such as `https://github.com/<owner>` (owner only, public GitHub) is now rejected rather than passed to modules.
- Console and web output gain an `Auditing ... (i of N)...` heading even for a single repository.
