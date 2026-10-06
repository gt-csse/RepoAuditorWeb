---
type: Change
title: Documented the overview and usage of RepoAuditorWeb in the README
description: The README describes the audit modules, experiences, common options, and YAML configuration files, with screenshots of the web experience.
tags: [docs, readme]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-05T20:49:43Z }
resource: README.md
---

# Summary

The README's `Overview` and `How to use` sections, previously `TODO` placeholders, describe what `RepoAuditorWeb` audits and how to run it.

# Motivation

The placeholders gave new users no indication of what the tool evaluates, which modules are available, or how to invoke it.

# Changes

- `Overview` lists the `GitHub`, `CommunityStandards`, and `ScientificSoftware` modules with their requirement counts.
- `How to use` covers the `web`, `tui`, `console`, and `json` experiences, common command line options and their environment variables, and `--config` YAML files.
- Added `docs/images/web_experience.png` and `docs/images/web_experience_results.png`; the README references them through `raw.githubusercontent.com` URLs on `main` so they render on PyPI as well as GitHub.
- `Installation` notes that `uvx` runs the tool without installing it.
