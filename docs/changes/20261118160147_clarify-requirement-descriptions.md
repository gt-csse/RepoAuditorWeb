---
type: Change
title: Clarify confusing requirement descriptions
description: Requirement descriptions now state what is actually evaluated, correcting text that implied rulesets were audited across every branch matching their pattern.
tags: [improved_text, requirements, rulesets]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-11-18T16:01:47Z }
resource: src/RepoAuditorWeb/lib/plugins/github_impl/ruleset_requirements
---

# Summary

The descriptions of the ruleset requirements now refer to "the evaluated branch" instead of "branches matching its pattern". Several other descriptions state more precisely what they check.

# Motivation

The ruleset query calls GitHub's `rules/branches/{branch}` endpoint, which returns the combined rules of every ruleset that applies to one branch. The old wording described a single ruleset and its target pattern, which the form never shows, and implied that every matching branch was checked. Other descriptions were vague about what they check, such as whether a merge method setting belongs to the repository or to a ruleset.

# Changes

- Ruleset requirements (BlockForcePushes, RequireAPullRequestBeforeMerging, RequireCodeScanningResults, RequireDeploymentsToSucceed, RequireLinearHistory, RequireSignedCommits, RequireStatusChecksToPass, RequiredApprovals, RestrictCreations, RestrictDeletions, RestrictUpdates) and AllowedMergeMethods refer to the evaluated branch.
- RequireCodeScanningResults and RequireDeploymentsToSucceed state that they gate changes merged into the evaluated branch, rather than the branch itself being merged.
- RestrictCreations refers to creating a branch with the evaluated branch's name, since the branch may not exist yet.
- AllowedMergeMethods' option help lists the valid methods.
- Description names the About section summary instead of describing search qualifiers; DefaultBranch states that only the branch's name is validated.
- AllowMergeCommits, AllowSquashMerging, and AllowRebaseMerging state that they validate the repository's setting.
- Updated the tests that assert the descriptions.

# Compatibility

- Text only: no requirement evaluates differently, and no option, parameter name, or json schema changes.
- Consumers that match on requirement descriptions, such as the `description` field of the json document, see the new text.
