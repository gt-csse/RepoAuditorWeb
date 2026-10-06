---
type: Change
title: Prefixed --version output with the application name
description: The --version option now prints "RepoAuditorWeb v<version>" instead of the bare version number.
tags: [cli, version]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T20:01:23Z }
resource: src/RepoAuditorWeb/impl/entry_point_utils.py
---

# Summary

`VersionCallback` writes `RepoAuditorWeb v<version>` to stdout, using the existing `APP_NAME` constant for the name.

# Motivation

A bare version number does not identify the tool that produced it when it appears in logs, bug reports, or captured terminal output. Prefixing the application name follows the convention of common CLI tools.

# Changes

- `VersionCallback` output changed from `<version>` to `RepoAuditorWeb v<version>`.
- Updated the expected output in `tests/entry_point_test.py` and `tests/impl/entry_point_utils_test.py`.
- Scripts that parse the bare version string from `--version` must strip the `RepoAuditorWeb v` prefix.
