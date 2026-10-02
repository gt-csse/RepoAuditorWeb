---
type: Change
title: Added CITATION requirement to ScientificSoftware
description: Replaced the ScientificSoftware placeholder module with a cloned-repository module whose query requires a CITATION or CITATIONS file, and extended FileExistsRequirement to accept multiple filenames.
tags: [scientific-software, plugins, requirements]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-02T20:38:00Z }
resource: src/RepoAuditorWeb/lib/plugins/scientific_software_impl
---

# Summary

`ScientificSoftwareModule` now derives from `ClonedRepositoryModule` and runs a `Scientific Software` query containing a `Citation` requirement. The requirement succeeds when a `CITATION` or `CITATIONS` file (any extension, case-insensitive) exists in the repository root or in `inst`. `FileExistsRequirement` accepts either a single filename or a list of filenames to support this.

# Motivation

Scientific software is expected to state how it should be cited so that authors receive credit and funders can measure impact; GitHub and Zenodo consume `CITATION.cff` directly. The ScientificSoftware module previously exposed only placeholder parameters (`five`, `six`) and performed no validation. Both `CITATION` and `CITATIONS` are in common use, and R packages store the file in `inst`, so a single filename and directory was insufficient.

# Changes

- `ScientificSoftwareModule` derives from `ClonedRepositoryModule`; its parameters are now `include`, `url`, `pat`, and `branch`, and it still requires explicit inclusion.
- Added `ScientificSoftwareQuery` and `requirements/citation.py` (`CitationRequirement`).
- `FileExistsRequirement` takes `filename_or_filenames: str | list[str]`, matches any of the names, reports them as `A or B` in messages, and raises `ValueError` when the list is empty.
- `test_ModuleIncludeOptionIsResolved` clones a local repository so the included module runs without network access.
- Common `--url`/`--pat`/`--branch` options are now forwarded to ScientificSoftware; the test asserting the opposite was removed.
- Added tests for the citation requirement, query, module, and multi-filename `FileExistsRequirement` behavior.
