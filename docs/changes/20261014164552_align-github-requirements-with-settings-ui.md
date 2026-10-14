---
type: Change
title: Renamed GitHub requirements to match the labels in GitHub's settings UI
description: GitHub standard and ruleset requirements are named after the setting labels GitHub displays, and their resolutions follow the current settings pages.
tags: [github, rulesets, requirements, resolutions, naming]
status: stable
generated: { by: claude-code/claude-opus-5-5, at: 2026-10-14T16:45:52Z }
resource: src/RepoAuditorWeb/lib/plugins/github_impl
---

# Summary

Requirements in the GitHub module's standard and ruleset queries are renamed after the label of the setting they audit (for example, `SupportIssues` becomes `Issues`, `RequiredReviewers` becomes `RequireReviewFromSpecificTeams`). Resolution steps are rewritten to match the current GitHub settings pages, and two ruleset requirements report `DoesNotApply` on repositories not owned by an organization.

# Motivation

Requirement names and resolution steps had drifted from what GitHub displays, so a user reading a result could not find the matching setting by name, and some steps referenced controls that no longer exist. Settings that depend on teams are only offered on organization-owned repositories, so failing them on a user-owned repository described a change that cannot be made.

# Changes

- Renamed standard requirements (module, class, and requirement name): `AutoMerge` → `AllowAutoMerge`, `MergeCommit` → `AllowMergeCommits`, `RebaseCommit` → `AllowRebaseMerging`, `SquashCommit` → `AllowSquashMerging`, `SuggestUpdatingPullRequestBranches` → `AlwaysSuggestUpdatingPullRequestBranches`, `DeleteBranchOnMerge` → `AutomaticallyDeleteHeadBranches`, `SupportDiscussions` → `Discussions`, `SupportIssues` → `Issues`, `SupportProjects` → `Projects`, `SupportPullRequests` → `PullRequests`, `SupportWikis` → `Wikis`, `SecretPushProtection` → `PushProtection`, `PublicPrivate` → `RepositoryVisibility`, `WebCommitSignoff` → `RequireContributorsToSignOffOnWebBasedCommits`, `Template` → `TemplateRepository`.
- Renamed ruleset requirements: `DismissStalePullRequestApprovals` → `DismissStalePullRequestApprovalsWhenNewCommitsArePushed`, `RequirePullRequests` → `RequireAPullRequestBeforeMerging`, `RequireApprovalOfMostRecentPush` → `RequireApprovalOfTheMostRecentReviewablePush`, `RequireApprovals` → `RequiredApprovals`, `RequireConversationResolution` → `RequireConversationResolutionBeforeMerging`, `RequireSuccessfulDeployments` → `RequireDeploymentsToSucceed`, `RequiredReviewers` → `RequireReviewFromSpecificTeams`, `RestrictDismissPullRequestReviews` → `RestrictWhoCanDismissPullRequestReviews`.
- `StandardQuery` orders requirements by settings page section and moves the web-based commit sign-off requirement to a new **Commits** section.
- `RulesetQuery.GetQueryData` always fetches the repository and stores `owner_type` in the query data.
- Added `parent_rule.GetNotOwnedByOrganizationResult`, used by `RequireReviewFromSpecificTeams` and `RestrictWhoCanDismissPullRequestReviews` to return `DoesNotApply` for repositories not owned by an organization.
- `RequireBranchesToBeUpToDateBeforeMerging` no longer returns `DoesNotApply` when the status checks rule names no check; it always evaluates the setting, and `parent_rule.GetStatusChecksResolutionPrefix` no longer takes `evaluate_all`.
- Added `parent_rule.STATUS_CHECKS_SETTINGS_STEP`, shared by status-check resolutions.
- Resolution text references **Rulesets settings**, **Show additional settings**, **Add checks**, **Add environments**, and the reviewer dialog as currently presented; the Dependabot security updates resolution drops a nonexistent **Save changes** step.
- Updated outdated GitHub documentation links in the community standards `Security` and JOSS `AutomatedTests` requirements.
- Renamed test files to match; `joss_impl/github_requirements/issues_test.py` became `joss_issues_test.py`.

# Compatibility

- Breaking for command-line and configuration users: requirement names appear in generated options (for example, `--GitHub-Template-skip` is now `--GitHub-TemplateRepository-skip`) and in experience output, so existing invocations and consumers that reference the old names must be updated.
- `RequireReviewFromSpecificTeams` and `RestrictWhoCanDismissPullRequestReviews` results change from failure to `DoesNotApply` on user-owned repositories.
