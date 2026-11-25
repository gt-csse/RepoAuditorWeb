---
type: Change
title: Fail fast instead of prompting for credentials when cloning
description: Cloning a repository that needs credentials now fails with an actionable error instead of prompting for a username on the launching terminal or through an askpass program.
tags: [bug, cloning, credentials]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-19T18:17:18Z }
resource: src/RepoAuditorWeb/lib/plugins/shared/cloned_repository_query.py
---

# Summary

ClonedRepositoryQuery clones with `GIT_TERMINAL_PROMPT=0` and an empty `GIT_ASKPASS`, so git fails immediately when it needs credentials it does not have. The clone error now also asks the user to check the URL and, when one was requested, the branch, and is no longer left indented by git's multi-line output.

# Motivation

Without saved credentials, cloning a nonexistent or private repository made git prompt for a username on the terminal that launched the app. Callers cannot see or answer that prompt, so the GUI appeared to hang on "Executing..." (#125). When launched from an environment that sets `GIT_ASKPASS` (e.g. a VS Code terminal), git instead opened a credentials dialog outside the app, bypassing its PAT field.

Failing fast makes the clone error far more common, which exposed that git's multi-line output prevented the message from being dedented.

# Changes

- `Repo.clone_from` receives `env={"GIT_ASKPASS": "", "GIT_TERMINAL_PROMPT": "0"}`, which GitPython merges into the inherited environment. An empty `GIT_ASKPASS` also overrides `core.askPass` and `SSH_ASKPASS`.
- The clone error message asks the user to ensure the repository URL is correct, and that the branch exists when one was requested.
- The clone error message is no longer left indented when git's error spans multiple lines.
- Tests assert the clone environment, both forms of the error message, and a multi-line git error.

# Compatibility

- Users who supplied credentials through git's terminal prompt or an askpass program (e.g. VS Code's) must now provide a PAT; saved credentials (credential helpers) still work.
