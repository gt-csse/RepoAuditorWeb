import textwrap

from RepoAuditorWeb.lib.plugins.github_impl.classic_branch_protection_requirements.ensure_not_used import (
    EnsureNotUsedRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/converting-branch-protections-to-rulesets"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the branch is governed by a ruleset rather than
    a classic branch protection rule. Both mechanisms protect a branch and GitHub enforces
    both, but rulesets are the framework GitHub continues to build upon.

    ## Reasons for this Default

    - Only a single branch protection rule applies to a branch at a time, so when several
      rules match it, the configuration that is enforced is not the union of them and is not
      evident from reading them. Rulesets layer instead, and every applicable ruleset is
      enforced.
    - A classic rule is visible only to those who can administer the repository, so
      contributors cannot confirm what governs the branch they are pushing to. Anyone with
      read access can view a repository's active rulesets.
    - A ruleset carries an enforcement status, so it can be disabled and re-enabled without
      being deleted and recreated. Suspending a classic rule means deleting it, which
      discards its configuration.
    - Rules that exist only for rulesets are unavailable while a classic rule governs the
      branch, including restrictions on commit metadata such as commit messages and author
      email addresses, and rules that target tags and pushes rather than branches.
    - Bypass is coarse for a classic rule: it applies to administrators and to roles holding
      the bypass permission unless bypassing is disallowed for everyone. A ruleset names the
      specific actors, teams, and apps that may bypass it.

    ## Reasons to Override this Default

    - A migration to rulesets is in progress and the classic rule is deliberately retained
      until the replacement ruleset has been verified, given that both are enforced
      together and the most restrictive form of a conflicting rule applies.
    - The repository is on a GitHub Enterprise Server release predating repository rulesets,
      where a classic rule is the only protection mechanism available.
    - Tooling outside the repository manages the classic rule through the branch protection
      APIs and has no ruleset equivalent, so removing the rule would cause that tooling to
      recreate or fail against it.

    Note that this requirement concerns which mechanism protects the branch, not how
    strictly it is protected. A classic rule may well be configured more strictly than the
    ruleset that would replace it.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: EnsureNotUsedRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    *,
    permit: bool = False,
    branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = EnsureNotUsedRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "branch": branch,
            "branch_protection_data": {},
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "permit": permit},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = EnsureNotUsedRequirement()

    assert requirement.name == "EnsureBranchProtectionsAreNotUsed"
    assert (
        requirement.description
        == "Validates whether the branch is protected by a ruleset rather than a classic branch protection rule, which GitHub no longer builds upon."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = EnsureNotUsedRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "permit"]
    assert parameters["permit"].type is bool
    assert parameters["permit"].default is False


# ----------------------------------------------------------------------
# The query produces data only when a classic rule governs the branch, so evaluating at all means
# the rule exists and the default outcome is an error.
def test_ClassicProtectionWhenProhibited():
    result = _Evaluate()

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_ClassicProtectionWhenPermitted():
    result = _Evaluate(permit=True)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_Rationale():
    assert _Evaluate().rationale == _RATIONALE
    assert _Evaluate(permit=True).rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate()

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Branches settings](https://github.com/gt-csse/RepoAuditorWeb/settings/branches) page.
        2) Click the **Convert to ruleset** button on the classic branch protection rule whose branch name pattern matches `main`.
        3) Enter a name for each ruleset that will be created.
        4) Review the **New behavior** section to confirm that the rules carry over as expected.
        5) Check the **Delete branch protection rule once migration is done** checkbox.
        6) Click the **Create ruleset** button.

        Note that **Require conversation resolution before merging** is not carried over,
        because rulesets express it within the pull request rule; enable it there afterwards
        if the classic rule required it.

        See [Converting branch protections to rulesets]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The classic rule matches by branch name pattern, so the resolution names the branch that was
# queried rather than assuming it is 'main'.
def test_ResolutionUsesBranchName():
    result = _Evaluate(branch="trunk")

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/branches)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = EnsureNotUsedRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "permit": False})

    assert result.result == EvaluateResultValue.Skipped
