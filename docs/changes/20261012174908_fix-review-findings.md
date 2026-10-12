---
type: Change
title: Fixed critical and high severity correctness and security defects identified in code review
description: Hardened the web experience, input validation, and credential handling; corrected ruleset evaluation when multiple rulesets apply; and fixed resource cleanup and state retention across the execution pipeline.
tags: [fix, security, web, github, rulesets, validation]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-12T17:49:08Z }
resource: src/RepoAuditorWeb/lib/execute.py
---

# Summary

Addresses the critical and high severity findings from a review of the codebase. The fixes span the web server, argument validation, GitHub API access, ruleset requirement evaluation, and the execution pipeline.

# Motivation

The review identified defects that could expose the PAT or allow other local or remote pages to drive the web server, requests whose paths could be altered by user input, requirements that reported incorrect results when more than one ruleset applied to a branch, and leaked resources or corrupted state between interactive runs.

# Changes

## Security

- The web server rejects requests whose `Host` is not `127.0.0.1` (DNS rebinding) and requires the token to load the page, which embeds the token and entered values; the window is opened with the token in its URL. Tokens are compared in constant time.
- JSON embedded in the page escapes `<` so that a value containing `</script>` cannot inject markup.
- The PAT is URL-encoded before being embedded in the clone URL, both raw and encoded forms are redacted from errors, and it is not embedded in `file://` URLs.
- The GitHub Enterprise API is accessed over `https` whenever a PAT is provided.
- A PAT file containing more than one token-like value is rejected without revealing its contents.
- `--url` must use `https://`, `http://`, or `file://`; GitHub owner and repository names are restricted to permitted characters, excluding `.` and `..`.
- `--branch` must be a valid git branch name, and branch names are percent-encoded in API paths.

## Ruleset evaluation

- `parent_rule.GetRule` is replaced by `GetRuleParameters`, which returns the parameters of every applicable rule. Each pull request requirement combines them according to what GitHub enforces: any ruleset enabling a boolean setting enforces it, the largest approval count applies, merge methods and dismissal actors are intersected, and required reviewers are unioned.
- Status checks, code scanning tools, deployment environments, and reviewers named by several rulesets are counted once.
- `EnsureNotUsed` reports that classic protection cannot be determined, rather than failing, when the token lacks administrative access.

## Execution and state

- `Module.CleanupModuleData` is a new abstract method invoked after a module's queries run; `GitHubModule` closes its HTTP session.
- Modules receive a deep copy of their arguments so that modifications do not alter the values retained by interactive experiences.
- `ClonedRepositoryQuery` removes the temporary directory when the clone fails.
- The web and TUI experiences parse submitted values before replacing the retained ones, so a parse failure leaves them intact; the web server guards the retained values with a lock.
- `StreamSink` retains events so that a reconnecting or late subscriber receives the complete stream; the run lock is released before the sink closes, and is released if starting the run fails.
- The page refreshes control disabling at the end of a run instead of rewiring listeners each time.
- The web experience waits for the server to start before opening the window and reports a failure to bind the port.

## Validation

- Numeric `min`/`max` bounds are enforced on values submitted through the form, and an empty value for an enumeration restores the default rather than raising.
- JOSS numeric parameters have a minimum of 0, and `PaperLength` rejects a minimum greater than its maximum.
- `FileExistsRequirement` requires at least one directory.
- `include` and `skip` are both reserved parameter names for modules and requirements.
- `License` handles a `null` license reported by GitHub.

## Documentation and tests

- README documents the JSON output schema and the `--url`, `--pat`, and `--branch` constraints; `docs/custom_modules.md` documents `CleanupModuleData`.
- Tests cover each fix.

# Compatibility

- Custom modules must implement `CleanupModuleData`; an implementation of `pass` is sufficient.
- Custom modules and requirements may no longer declare a parameter named `include` or `skip`.
- `--url` values without a supported scheme, and invalid branch names, now raise errors.
- `ClassicBranchProtectionQuery` stores its data under `response` rather than `branch_protection_data`.
- Requests to the web server's `/` endpoint require the `token` query parameter.
