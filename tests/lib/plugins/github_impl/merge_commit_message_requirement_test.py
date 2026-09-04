import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.merge_commit_message_requirement import (
    MergeCommitMessageRequirement,
    Values,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-merging-for-pull-requests"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the merge commit's subject is the pull request
    title and that its body is empty (the **Pull request title** option).

    Note that this differs from the state of a newly created repository, which uses the
    **Default message** option.

    ## Reasons for this Default

    - The classic subject, `Merge pull request #123 from <owner>/<branch>`, describes the
      mechanics of the merge rather than the change it introduced. A log of such subjects
      conveys only that merges happened, so the reader has to open each one to learn what it
      was. The pull request title states the change, which is what a subject line is for.
    - The branch name in the classic subject is transient. It identifies a ref that is
      typically deleted once the pull request merges, so it dates the history with a name that
      no longer resolves while displacing the description of the change.
    - Git convention treats the first line as a short summary, and tooling relies on it:
      `git log --oneline`, `git shortlog`, blame annotations, and most review interfaces show
      the subject alone. A subject that omits the change makes each of these less informative.
    - An empty body keeps the pull request description in one place. The description is
      maintained on the pull request, where it can be corrected after the fact, whereas a copy
      committed into the history cannot be amended once the commit is on the base branch.
    - The pull request number remains in the subject under this option, so the commit still
      links back to its discussion and review.

    ## Reasons to Override this Default

    - The project wants the commit to be self-contained, so that the reasoning survives without
      access to the pull request. This matters when the history may be read outside GitHub, or
      when the repository could move to a host where the pull requests do not follow
      (`pull_request_title_and_description`).
    - Tooling that generates release notes or changelogs from commit bodies has nothing to read
      when the body is empty (`pull_request_title_and_description`).
    - The project relies on the classic subject's branch name, or on tooling that parses the
      `Merge pull request #N` form, and changing it would break that (`default_message`).

    Note that this setting only supplies the message GitHub pre-fills; a user with write
    access can edit it before confirming the merge, so it establishes a default rather than
    enforcing a format. Note also that it applies to merge commits alone, and that the squash
    and rebase methods are configured separately.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: MergeCommitMessageRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    value: Values = Values.PullRequestTitle,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = MergeCommitMessageRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "value": value},
    )


# ----------------------------------------------------------------------
def _Response(title: str, message: str, *, allow_merge_commit: bool = True) -> dict:
    return {
        "allow_merge_commit": allow_merge_commit,
        "merge_commit_title": title,
        "merge_commit_message": message,
    }


# ----------------------------------------------------------------------
def test_Construct():
    requirement = MergeCommitMessageRequirement()

    assert requirement.name == "MergeCommitMessage"
    assert (
        requirement.description
        == "Validates the default commit message offered when a pull request is merged with a merge commit."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = MergeCommitMessageRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is Values
    assert parameters["value"].default == Values.PullRequestTitle


# ----------------------------------------------------------------------
def test_ValuesMembers():
    assert [(value.name, value.value) for value in Values] == [
        ("DefaultMessage", "default_message"),
        ("PullRequestTitle", "pull_request_title"),
        ("PullRequestTitleAndDescription", "pull_request_title_and_description"),
    ]


# ----------------------------------------------------------------------
# Each human-facing value corresponds to a pairing of the two API fields, and the pairing is what
# the requirement compares against.
@pytest.mark.parametrize(
    ("value", "title", "message"),
    [
        (Values.DefaultMessage, "MERGE_MESSAGE", "PR_TITLE"),
        (Values.PullRequestTitle, "PR_TITLE", "BLANK"),
        (Values.PullRequestTitleAndDescription, "PR_TITLE", "PR_BODY"),
    ],
)
def test_MatchingValues(value, title, message):
    result = _Evaluate(_Response(title, message), value=value)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# 'PR_TITLE' means different things in each field, so a value that matches the expected title is
# still a failure when the message does not match.
def test_MatchingTitleWithMismatchedMessage():
    result = _Evaluate(_Response("PR_TITLE", "PR_BODY"), value=Values.PullRequestTitle)

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
def test_MismatchedTitleWithMatchingMessage():
    result = _Evaluate(_Response("MERGE_MESSAGE", "BLANK"), value=Values.PullRequestTitle)

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
# A newly created repository uses the 'Default message' option, which the default value rejects.
def test_NewRepositoryDefaultFails():
    result = _Evaluate(_Response("MERGE_MESSAGE", "PR_TITLE"))

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's default merge commit message is 'Default message', but the requirement "
        "specifies it must be 'Pull request title'."
    )


# ----------------------------------------------------------------------
# The context names the repository's setting by its dropdown label rather than by the API values
# that GitHub reports.
@pytest.mark.parametrize(
    ("title", "message", "label"),
    [
        ("MERGE_MESSAGE", "PR_TITLE", "Default message"),
        ("PR_TITLE", "PR_BODY", "Pull request title and description"),
    ],
)
def test_ContextUsesUiLabel(title, message, label):
    result = _Evaluate(_Response(title, message))

    assert result.context == (
        f"The repository's default merge commit message is '{label}', but the requirement "
        "specifies it must be 'Pull request title'."
    )


# ----------------------------------------------------------------------
# The requirement's own value is reported by its dropdown label too.
@pytest.mark.parametrize(
    ("value", "label"),
    [
        (Values.DefaultMessage, "Default message"),
        (Values.PullRequestTitle, "Pull request title"),
        (Values.PullRequestTitleAndDescription, "Pull request title and description"),
    ],
)
def test_ContextUsesUiLabelForRequiredValue(value, label):
    result = _Evaluate(_Response("MERGE_MESSAGE", "BLANK"), value=value)

    assert result.context is not None
    assert result.context.endswith(f"but the requirement specifies it must be '{label}'.")


# ----------------------------------------------------------------------
# A pairing that the dropdown cannot produce has no label to report, so the API values are named
# directly rather than being forced onto the nearest option.
def test_UnreachablePairing():
    result = _Evaluate(_Response("MERGE_MESSAGE", "PR_BODY"))

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's default merge commit message is title 'MERGE_MESSAGE' with message "
        "'PR_BODY', but the requirement specifies it must be 'Pull request title'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate(_Response("MERGE_MESSAGE", "PR_TITLE"))

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Ensure that the **Allow merge commits** checkbox is checked.
        4) Select **Pull request title** in the dropdown beneath it.

        See [Configuring commit merging for pull requests]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution names the dropdown label rather than the API value, because the label is what the
# user selects.
@pytest.mark.parametrize(
    ("value", "label"),
    [
        (Values.DefaultMessage, "Default message"),
        (Values.PullRequestTitle, "Pull request title"),
        (Values.PullRequestTitleAndDescription, "Pull request title and description"),
    ],
)
def test_ResolutionUsesUiLabel(value, label):
    result = _Evaluate(_Response("INVALID", "INVALID"), value=value)

    assert result.resolution is not None
    assert f"4) Select **{label}** in the dropdown beneath it." in result.resolution


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate(
        _Response("MERGE_MESSAGE", "PR_TITLE"),
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome or the selected value.
@pytest.mark.parametrize("value", list(Values))
def test_Rationale(value):
    result = _Evaluate(_Response("PR_TITLE", "BLANK"), value=value)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate(_Response("MERGE_MESSAGE", "PR_TITLE"))

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# GitHub omits the merge commit message settings for a caller without push access, so an absent
# key means the value is unknown rather than a particular setting. A missing token is the user's to
# correct, so it warns.
def test_MissingValuesWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's merge commit message settings are not visible because no Personal Access Token was provided."
    )


# ----------------------------------------------------------------------
# The resolution comes from the shared helper, which explains how to supply a token.
def test_MissingValuesWithoutPatResolution():
    result = _Evaluate({}, pat=None)

    assert result.resolution is not None
    assert "`--GitHub-pat`" in result.resolution


# ----------------------------------------------------------------------
# A token that lacks push access reads the repository but still does not see these settings,
# which is a misconfiguration of the token rather than a repository failure.
def test_MissingValuesWithPat():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's merge commit message settings are not visible because the Personal Access Token provided does not grant push access to the repository."
    )


# ----------------------------------------------------------------------
# The two fields are reported together, so either one being absent means the settings are not
# visible.
@pytest.mark.parametrize(
    "response",
    [
        {"allow_merge_commit": True, "merge_commit_title": "PR_TITLE"},
        {"allow_merge_commit": True, "merge_commit_message": "BLANK"},
    ],
)
def test_PartiallyMissingValues(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's merge commit message settings are not visible because the Personal Access Token provided does not grant push access to the repository."
    )


# ----------------------------------------------------------------------
# The rationale explains a default that could not be evaluated, so it is omitted when the settings
# are not visible; the problem is the token rather than the repository's configuration.
@pytest.mark.parametrize("pat", [None, "my-pat"])
def test_MissingValuesHaveNoRationale(pat):
    result = _Evaluate({}, pat=pat)

    assert result.rationale is None


# ----------------------------------------------------------------------
def test_ResultAttributes():
    requirement = MergeCommitMessageRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": _Response("PR_TITLE", "BLANK"),
            "session": GitHubSession("https://github.com/gt-csse/RepoAuditorWeb", "my-pat"),
        },
        {"skip": False, "value": Values.PullRequestTitle},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.requirement is requirement


# ----------------------------------------------------------------------
# The setting only governs the message offered for merge commits, so it has nothing to evaluate in
# a repository that disallows the method.
@pytest.mark.parametrize("value", list(Values))
def test_MergeCommitsDisallowed(value):
    result = _Evaluate(_Response("MERGE_MESSAGE", "PR_TITLE", allow_merge_commit=False), value=value)

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The repository does not allow merge commits, so no default merge commit message is offered."
    )


# ----------------------------------------------------------------------
# There is nothing for the user to correct when the requirement does not apply, so no resolution is
# offered; the rationale still explains the default that was not evaluated.
def test_MergeCommitsDisallowedResolutionAndRationale():
    result = _Evaluate(_Response("PR_TITLE", "BLANK", allow_merge_commit=False))

    assert result.resolution is None
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# GitHub retains the message setting while merge commits are disallowed, so a matching value is
# reported as inapplicable rather than as a success.
def test_MergeCommitsDisallowedWithMatchingValue():
    result = _Evaluate(_Response("PR_TITLE", "BLANK", allow_merge_commit=False))

    assert result.result == EvaluateResultValue.DoesNotApply


# ----------------------------------------------------------------------
# The checkbox is restricted too, so a caller that cannot see it cannot determine whether the
# requirement applies.
@pytest.mark.parametrize(
    ("pat", "expected_result"),
    [
        (None, EvaluateResultValue.Warning),
        ("my-pat", EvaluateResultValue.Error),
    ],
)
def test_MissingAllowMergeCommit(pat, expected_result):
    result = _Evaluate({"merge_commit_title": "PR_TITLE", "merge_commit_message": "BLANK"}, pat=pat)

    assert result.result == expected_result
    assert result.context is not None
    assert "merge commit message settings are not visible" in result.context


# ----------------------------------------------------------------------
def test_Skip():
    requirement = MergeCommitMessageRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"skip": True, "value": Values.PullRequestTitle},
    )

    assert result.result == EvaluateResultValue.Skipped
