---
type: Change
title: README explains uvx and the package exposes a RepoAuditorWeb command
description: The README explains what uvx is and how to obtain it, moves the PAT permissions section after configuration files, and the package adds a RepoAuditorWeb console script alongside repoauditorweb.
tags: [documentation, readme, uvx, console-scripts]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-15T15:45:32Z }
resource: README.md
---

# Summary

The README's quick-start now explains that `uvx` is part of `uv`, that it runs `RepoAuditorWeb` without a prior install, and where to install `uv` if it is missing. The `PAT Permissions` section moves below `Configuration Files`, and the Installation section states up front that installation is unnecessary with `uvx`. `pyproject.toml` adds a `RepoAuditorWeb` console script that maps to the same entry point as `repoauditorweb`.

# Motivation

Readers unfamiliar with `uv` encountered `uvx` in the first example with no explanation of what it is or how to obtain it. `uvx <name>` runs the executable matching the requested package name, so `uvx RepoAuditorWeb` failed because the package only provided a lowercase `repoauditorweb` executable; the alias makes the package name and command name interchangeable.

# Changes

- `README.md`: added a note after the first `uvx` example describing `uvx` and linking to the `uv` installation guide and the Installation section.
- `README.md`: moved `PAT Permissions` after `Configuration Files`; content is unchanged.
- `README.md`: reordered the Installation section so the `uvx` note precedes the installation table.
- `pyproject.toml`: added `RepoAuditorWeb = "RepoAuditorWeb.__main__:app"` under `[project.scripts]`.

# Compatibility

- Additive only; the existing `repoauditorweb` command is unchanged.
