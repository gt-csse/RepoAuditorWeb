---
type: Change
title: Missing PAT resolution references the --pat option
description: The resolution shown when a requirement needs a GitHub PAT now names the existing `--pat` command line option instead of the nonexistent `--GitHub-pat`.
tags: [github, pat, resolution, cli]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-12T21:18:12Z }
resource: src/RepoAuditorWeb/lib/plugins/github_impl/standard_requirements/restricted_value.py
---

# Summary

When a GitHub requirement cannot be evaluated without a Personal Access Token, its resolution now tells the user to provide the token via the `--pat` command line argument or the `REPO_AUDITOR_WEB_GITHUB_PAT` environment variable.

# Motivation

The resolution named `--GitHub-pat`, which does not exist; the PAT is a common option provided via `--pat`. Users following the advice were rejected with `No such option: --GitHub-pat`.

# Changes

- `_CreateNoPatResolution` in `restricted_value.py` references `--pat`.
- Updated the resolution assertions in the `standard_requirements` tests.

# Compatibility

- Resolution text only; the `--pat` option and environment variable are unchanged.
