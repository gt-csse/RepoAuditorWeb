---
type: Change
title: PAT must be provided as a path to a file
description: The --pat option, the REPO_AUDITOR_WEB_GITHUB_PAT environment variable, and the web form's PAT field accept only the path to a file containing the token, and the json document records that path instead of a redacted value.
tags: [security, pat, cli, json, web, breaking-change]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-13T16:53:41Z }
resource: src/RepoAuditorWeb/lib/plugins/shared/repository_arguments.py
---

# Summary

The PAT is now always read from a file. `ResolvePat` rejects any value that does not name an existing file with `'pat' must be the path to a file containing a Personal Access Token.`, without echoing the value. The console, json, and web experiences, and wildcard url expansion, all resolve the PAT through `ResolvePat`, so the rule applies to each of them. Because the provided value is now a path rather than a credential, the json document includes it in `common_arguments.pat` instead of `***`, and the document's schema version is incremented to 4.

# Motivation

A token entered directly is exposed in shell history, process listings, environment dumps, and the web page, which embeds the values entered. Accepting only a file keeps the token out of those places. The error omits the value in case a token was entered by mistake. With only a path accepted, redacting it in the json document no longer protects anything, while recording it shows which token file an audit used.

# Changes

- `ResolvePat` requires an existing file and expands `~`, since values entered in the web form are not expanded by a shell.
- A file that does not hold a single token, including a blank one, is rejected with `'<file>' does not contain a Personal Access Token.`
- The PAT provided on the command line, through the environment variable, or in a config file is validated at startup, so an invalid one fails before any experience runs or the web form is populated. The path, not the token, is forwarded to the experiences.
- The json document records the PAT file path as provided. `json_experience_v4.schema.json` allows any string or null for `pat`; `json_experience_v3.schema.json` is retained for documents written against it.
- Updated the `--pat` help text, the README, and the resolution shown when no PAT is provided.
- Tests that passed a token directly now write it to a file; added tests for rejected values.

# Compatibility

- Breaking: `--pat <token>` and `REPO_AUDITOR_WEB_GITHUB_PAT=<token>` now fail; save the token to a file and pass its path instead.
- Breaking: json documents reference schema version 4, and `common_arguments.pat` holds the PAT file path instead of `***`.
- The option, environment variable, and form field names are unchanged.
