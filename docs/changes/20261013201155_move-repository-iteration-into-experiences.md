---
type: Change
title: Moved per-repository iteration from the entry point into each experience
description: Each experience receives the resolved repository urls and iterates them through a shared InvokeForEachRepository, so the entry point no longer contains experience-specific logic.
tags: [cli, json, web, multi-repository, refactor]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-13T20:11:55Z }
resource: src/RepoAuditorWeb/impl/repositories.py
---

# Summary

The entry point resolves the repository urls and passes them to the selected experience, which iterates them via `InvokeForEachRepository` in `impl/repositories.py`. Logic previously embedded in `__main__.py` for specific experiences (the json document, the web warning, and per-repository port resolution) now lives in the experience that requires it.

# Motivation

The wildcard url change placed the repository loop in `EntryPoint`, along with json-specific state (entries, error, document writing) and web-specific behavior (the multi-window warning and per-repository ports). This coupled the entry point to the internals of each experience. Moving the iteration into the experiences keeps each experience self-contained and leaves the entry point responsible only for parsing and dispatch.

# Changes

- Added `InvokeForEachRepository`, which runs a callback per url under an `Auditing '<url>' (i of N)...` heading with exceptions suppressed so a failure does not stop the remaining repositories. The first repository receives a deep copy of the arguments and later repositories receive `DisableModulesWithoutUrl`, so the caller's arguments are never modified.
- Each `ExecuteExperience` accepts `urls: list[str | None]` and `port: int | None`; `common_arguments` no longer contains `url`, which is added per repository.
- Console and web experiences moved their single-repository logic into a private `_ExecuteRepository`.
- The web experience emits the multi-window warning and calls `ResolvePort` per repository.
- The json experience collects entries itself and writes the document from a `finally` clause; `WriteDocument` became private as `_WriteDocument` and writes the stderr separator. `CreateRepositoryEntry` remains public.
- `__main__.py` reduced to resolving inputs and calling the experience.
- Tests moved from `entry_point_test.py` to the experience and `repositories` tests.

# Compatibility

- A failure before auditing begins (such as an invalid wildcard url) is reported as an error and the json document is no longer written; previously a document with only a top-level `error` was written. The top-level `error` now describes failures that stop the run after auditing begins, such as an interruption. `README.md` was updated accordingly.
- `json_experience.WriteDocument` was removed from the public interface.
