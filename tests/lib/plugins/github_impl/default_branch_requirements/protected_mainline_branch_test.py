import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.default_branch_requirements.protected_mainline_branch import (
    ProtectedMainlineBranchRequirement,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_CREATE_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/creating-rulesets-for-a-repository"
)

_MANAGE_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository"
    "/managing-rulesets/managing-rulesets-for-a-repository"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the default branch is protected. GitHub reports
    the branch as protected when a branch protection rule or a ruleset targets it, so either
    mechanism satisfies this requirement.

    ## Reasons for this Default

    - An unprotected default branch accepts a force push from anyone with write access, which
      replaces history that existing clones and published references already depend on. The
      commits the push abandoned are no longer reachable, so recovering them requires knowing
      that they existed.
    - Protecting the branch is what makes the rest of the repository's review configuration
      binding. Settings such as the merge methods and auto-merge describe how a pull request
      may be merged, but they do not require that a change arrive through one; a direct push
      bypasses them entirely.
    - The default branch is the branch a clone checks out, the base branch proposed for new
      pull requests, and the branch consumers reference by name, so it is the branch where
      rewritten history is most widely observed.
    - Protection is the mechanism the rules worth having later are attached to, including
      required reviews, status checks, and linear history. This requirement establishes that
      mechanism rather than any particular rule.

    ## Reasons to Override this Default

    - The repository is private and owned by an account on a plan that offers neither branch
      protection rules nor rulesets for private repositories, in which case protecting the
      branch is a purchasing decision rather than a configuration one.
    - The repository is a scratch, mirror, or generated repository whose default branch is
      rewritten by design, where blocking force pushes prevents the repository from serving
      its purpose.
    - Protection is enforced where GitHub does not report it, such as a pre-receive hook on
      an Enterprise Server instance, so the branch is governed while this value remains
      false.

    Note that this requirement establishes only that the branch is protected, not what the
    protection requires. A rule that targets the branch and enables nothing beyond the
    defaults still reports the branch as protected while permitting unreviewed direct pushes.

    Note also that protection does not by itself constrain everyone. A classic branch
    protection rule does not apply to those who can bypass it unless **Do not allow
    bypassing the above settings** is enabled, and a ruleset does not apply to the actors
    named in its bypass list.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: ProtectedMainlineBranchRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    prohibit: bool = False,
    default_branch: str = "main",
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = ProtectedMainlineBranchRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": response,
            "default_branch": default_branch,
            "session": GitHubSession(url, "my-pat"),
        },
        {"skip": False, "prohibit": prohibit},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = ProtectedMainlineBranchRequirement()

    assert requirement.name == "ProtectedMainlineBranch"
    assert (
        requirement.description
        == "Validates whether the default branch is protected by a branch protection rule or a ruleset, which blocks force pushes and deletion."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = ProtectedMainlineBranchRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("protected", "prohibit"),
    [(True, False), (False, True)],
)
def test_MatchingValue(protected, prohibit):
    result = _Evaluate({"protected": protected}, prohibit=prohibit)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
@pytest.mark.parametrize("protected", [True, False])
def test_Rationale(protected):
    result = _Evaluate({"protected": protected})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_UnprotectedWhenRequired():
    result = _Evaluate({"protected": False})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ProtectedWhenProhibited():
    result = _Evaluate({"protected": True}, prohibit=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
# GitHub reports 'protected' for any caller with read access, so an absent value is a branch that
# is not protected rather than one whose protection is not visible.
def test_MissingValueIsUnprotected():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"protected": False})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Click the **New ruleset** button, then click **New branch ruleset**.
        3) Enter `'main' - ruleset` in the **Ruleset name** field.
        4) Set the enforcement status to **Active**.
        5) Click the **Add target** button in the **Target branches** section, then choose **Include default branch**.
        6) Click the **Create** button at the bottom of the page.

        A classic branch protection rule whose branch name pattern matches
        `main` is an equivalent alternative, created from the repository's
        [Branches settings](https://github.com/gt-csse/RepoAuditorWeb/settings/branches) page via the **Add classic branch protection rule** button.

        See [Creating rulesets for a repository]({_CREATE_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to remove the protection when the branch must not be protected.
def test_ErrorResolutionWhenProhibited():
    result = _Evaluate({"protected": True}, prohibit=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [Rules settings](https://github.com/gt-csse/RepoAuditorWeb/settings/rules) page.
        2) Delete each ruleset that targets `main`, or set its enforcement status to **Disabled**.
        3) Open the repository's [Branches settings](https://github.com/gt-csse/RepoAuditorWeb/settings/branches) page.
        4) Delete each classic branch protection rule whose branch name pattern matches `main`.

        See [Managing rulesets for a repository]({_MANAGE_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The classic rule matches by branch name pattern, so the resolution names the branch that was
# queried rather than assuming it is 'main'.
@pytest.mark.parametrize("prohibit", [False, True])
def test_ResolutionUsesDefaultBranchName(prohibit):
    result = _Evaluate(
        {"protected": prohibit},
        prohibit=prohibit,
        default_branch="trunk",
    )

    assert result.resolution is not None
    assert "`trunk`" in result.resolution
    assert "`main`" not in result.resolution


# ----------------------------------------------------------------------
# The settings urls are derived from the repository under audit rather than hard-coded, so they
# point at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"protected": False}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings/rules)" in result.resolution
    assert "(https://github.example.com/my-org/my-repo/settings/branches)" in result.resolution


# ----------------------------------------------------------------------
def test_Skip():
    requirement = ProtectedMainlineBranchRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "prohibit": False})

    assert result.result == EvaluateResultValue.Skipped
