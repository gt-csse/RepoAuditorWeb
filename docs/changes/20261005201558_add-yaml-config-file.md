---
type: Change
title: Added a YAML config file option to the command line
description: Commands built by dynamic_command accept a --config option that loads parameter values from a YAML file.
tags: [cli, config]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T20:15:58Z }
resource: src/RepoAuditorWeb/impl/entry_point_utils.py
---

# Summary

`dynamic_command` wraps the synthesized command with `typer_config.use_yaml_config`, adding a `--config` option that reads parameter values from a YAML file. Values on the command line take precedence over values in the file.

# Motivation

Each module and requirement contributes its own command-line options, so a full audit configuration produces long, error-prone command lines. A config file lets a configuration be stored, reused, and shared.

# Changes

- Added the `typer-config[yaml]` dependency.
- `dynamic_command` applies `use_yaml_config` to the synthesized `Invoker` signature rather than the original function, because the decorator appends its parameter and the original function ends with `**kwargs`.
- `--config` is moved to the first position in the signature so it is listed first in help; all parameters are keyword-only, so order is otherwise insignificant.
- Config file keys are the python parameter names (for example `GitHub_branch`), not the option names (`--GitHub-branch`).
- Added tests for loading values from a config file, command-line precedence, invalid config values, and the position of `--config` in help.
