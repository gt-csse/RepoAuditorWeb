import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.squash_commit_message_requirement import (
    SquashCommitMessageRequirement,
    Values,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the squash commit's subject is the pull request
    title and that its body contains the messages of the commits being squashed (the **Pull
    request title and commit details** option).

    Note that this differs from the state of a newly created repository, which uses the
    **Default message** option.

    ## Reasons for this Default

    - Squashing discards the commits it replaces, so any information recorded only in their
      messages is lost when the branch is deleted. This option is the only one that carries
      those messages onto the base branch, which keeps the reasoning behind each step of the
      change reachable from the history rather than from a branch that no longer exists.
    - A pull request approved as a series of commits is reviewed as that series. Retaining the
      messages preserves the account of the work that the reviewer read, so the commit that
      lands describes the same change the review covered.
    - The pull request title is a stable subject. The **Default message** option takes the
      subject from the single commit when a branch has one commit and from the pull request
      title when it has more, so the subject of a squash commit depends on how the branch
      happened to be structured. Fixing it to the title makes `git log --oneline` and
      `git shortlog` consistent across merges.
    - The pull request number is appended to the subject under this option, so the commit
      still links back to its discussion and review.
    - The commit body is the copy that survives without GitHub. Repository archives, mirrors,
      and clones carry commit messages, while pull request bodies and their commit lists are
      host metadata that a `git clone` does not include.

    ## Reasons to Override this Default

    - The branch's commits are fixups, merges of the base branch, or work-in-progress markers
      that carry no meaning after review, in which case copying them into the body adds noise
      rather than information (`pull_request_title` or
      `pull_request_title_and_description`).
    - The project maintains the account of the change in the pull request description instead
      of in the commits, and wants that description to be what lands
      (`pull_request_title_and_description`).
    - Tooling generates release notes from commit bodies and expects a curated body rather
      than a concatenation of the branch's messages (`pull_request_title_and_description`).
    - The project relies on a single-commit branch's own subject and body reaching the base
      branch unaltered (`default_message`).

    Note that this setting only supplies the message GitHub pre-fills; a user with write
    access can edit it before confirming the merge, so it establishes a default rather than
    enforcing a format. Note also that it applies to squash commits alone, and that the merge
    commit method is configured separately. A squash commit carries no information about the
    authorship or signatures of the commits it replaces regardless of this setting, which is
    a property of the method rather than of the message.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SquashCommitMessageRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    value: Values = Values.PullRequestTitleAndCommitDetails,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
    pat: str | None = "my-pat",
) -> EvaluateResult:
    requirement = SquashCommitMessageRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, pat)},
        {"skip": False, "value": value},
    )


# ----------------------------------------------------------------------
def _Response(title: str, message: str, *, allow_squash_merge: bool = True) -> dict:
    return {
        "allow_squash_merge": allow_squash_merge,
        "squash_merge_commit_title": title,
        "squash_merge_commit_message": message,
    }


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SquashCommitMessageRequirement()

    assert requirement.name == "SquashCommitMessage"
    assert (
        requirement.description
        == "Validates the default commit message offered when a pull request is merged by squashing."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
# The default carries the squashed commits' messages onto the base branch, which is the only option
# that preserves information recorded solely in those commits.
def test_GetParameters():
    parameters = SquashCommitMessageRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is Values
    assert parameters["value"].default == Values.PullRequestTitleAndCommitDetails


# ----------------------------------------------------------------------
def test_ValuesMembers():
    assert [(value.name, value.value) for value in Values] == [
        ("DefaultMessage", "default_message"),
        ("PullRequestTitle", "pull_request_title"),
        ("PullRequestTitleAndCommitDetails", "pull_request_title_and_commit_details"),
        ("PullRequestTitleAndDescription", "pull_request_title_and_description"),
    ]


# ----------------------------------------------------------------------
# Each human-facing value corresponds to a pairing of the two API fields, and the pairing is what
# the requirement compares against.
@pytest.mark.parametrize(
    ("value", "title", "message"),
    [
        (Values.DefaultMessage, "COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"),
        (Values.PullRequestTitle, "PR_TITLE", "BLANK"),
        (Values.PullRequestTitleAndCommitDetails, "PR_TITLE", "COMMIT_MESSAGES"),
        (Values.PullRequestTitleAndDescription, "PR_TITLE", "PR_BODY"),
    ],
)
def test_MatchingValues(value, title, message):
    result = _Evaluate(_Response(title, message), value=value)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# 'COMMIT_MESSAGES' is shared by two options, so a value that matches the expected message is still
# a failure when the title does not match.
def test_MatchingMessageWithMismatchedTitle():
    result = _Evaluate(
        _Response("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"),
        value=Values.PullRequestTitleAndCommitDetails,
    )

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
# 'PR_TITLE' is shared by three options, so a matching title is not sufficient either.
def test_MatchingTitleWithMismatchedMessage():
    result = _Evaluate(_Response("PR_TITLE", "PR_BODY"), value=Values.PullRequestTitleAndCommitDetails)

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
# A newly created repository uses the 'Default message' option, which the default value rejects.
def test_NewRepositoryDefaultFails():
    result = _Evaluate(_Response("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"))

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's default squash commit message is 'Default message', but the requirement "
        "specifies it must be 'Pull request title and commit details'."
    )


# ----------------------------------------------------------------------
# The context names the repository's setting by its dropdown label rather than by the API values
# that GitHub reports.
@pytest.mark.parametrize(
    ("title", "message", "label"),
    [
        ("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES", "Default message"),
        ("PR_TITLE", "BLANK", "Pull request title"),
        ("PR_TITLE", "PR_BODY", "Pull request title and description"),
    ],
)
def test_ContextUsesUiLabel(title, message, label):
    result = _Evaluate(_Response(title, message))

    assert result.context == (
        f"The repository's default squash commit message is '{label}', but the requirement "
        "specifies it must be 'Pull request title and commit details'."
    )


# ----------------------------------------------------------------------
# The requirement's own value is reported by its dropdown label too.
@pytest.mark.parametrize(
    ("value", "label"),
    [
        (Values.DefaultMessage, "Default message"),
        (Values.PullRequestTitle, "Pull request title"),
        (Values.PullRequestTitleAndCommitDetails, "Pull request title and commit details"),
        (Values.PullRequestTitleAndDescription, "Pull request title and description"),
    ],
)
def test_ContextUsesUiLabelForRequiredValue(value, label):
    result = _Evaluate(_Response("INVALID", "INVALID"), value=value)

    assert result.context is not None
    assert result.context.endswith(f"but the requirement specifies it must be '{label}'.")


# ----------------------------------------------------------------------
# A pairing that the dropdown cannot produce has no label to report, so the API values are named
# directly rather than being forced onto the nearest option.
def test_UnreachablePairing():
    result = _Evaluate(_Response("COMMIT_OR_PR_TITLE", "PR_BODY"))

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's default squash commit message is title 'COMMIT_OR_PR_TITLE' with message "
        "'PR_BODY', but the requirement specifies it must be 'Pull request title and commit details'."
    )


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate(_Response("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"))

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Pull Requests** section.
        3) Ensure that the **Allow squash merging** checkbox is checked.
        4) Select **Pull request title and commit details** in the dropdown beneath it.

        See [Configuring commit squashing for pull requests]({_DOCUMENTATION_URL})
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
        (Values.PullRequestTitleAndCommitDetails, "Pull request title and commit details"),
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
        _Response("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"),
        url="https://github.example.com/my-org/my-repo",
    )

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome or the selected value.
@pytest.mark.parametrize("value", list(Values))
def test_Rationale(value):
    result = _Evaluate(_Response("PR_TITLE", "COMMIT_MESSAGES"), value=value)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate(_Response("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES"))

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# GitHub omits the squash commit message settings for a caller without push access, so an absent
# key means the value is unknown rather than a particular setting. A missing token is the user's to
# correct, so it warns.
def test_MissingValuesWithoutPat():
    result = _Evaluate({}, pat=None)

    assert result.result == EvaluateResultValue.Warning
    assert result.context == (
        "The repository's squash commit message settings are not visible because no Personal Access Token was provided."
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
        "The repository's squash commit message settings are not visible because the Personal Access Token provided does not grant push access to the repository."
    )


# ----------------------------------------------------------------------
# The two fields are reported together, so either one being absent means the settings are not
# visible.
@pytest.mark.parametrize(
    "response",
    [
        {"allow_squash_merge": True, "squash_merge_commit_title": "PR_TITLE"},
        {"allow_squash_merge": True, "squash_merge_commit_message": "COMMIT_MESSAGES"},
    ],
)
def test_PartiallyMissingValues(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's squash commit message settings are not visible because the Personal Access Token provided does not grant push access to the repository."
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
    requirement = SquashCommitMessageRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": _Response("PR_TITLE", "COMMIT_MESSAGES"),
            "session": GitHubSession("https://github.com/gt-csse/RepoAuditorWeb", "my-pat"),
        },
        {"skip": False, "value": Values.PullRequestTitleAndCommitDetails},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.requirement is requirement


# ----------------------------------------------------------------------
# The setting only governs the message offered for squash commits, so it has nothing to evaluate in
# a repository that disallows the method.
@pytest.mark.parametrize("value", list(Values))
def test_SquashMergingDisallowed(value):
    result = _Evaluate(
        _Response("COMMIT_OR_PR_TITLE", "COMMIT_MESSAGES", allow_squash_merge=False),
        value=value,
    )

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == (
        "The repository does not allow squash merging, so no default squash commit message is offered."
    )


# ----------------------------------------------------------------------
# There is nothing for the user to correct when the requirement does not apply, so no resolution is
# offered; the rationale still explains the default that was not evaluated.
def test_SquashMergingDisallowedResolutionAndRationale():
    result = _Evaluate(_Response("PR_TITLE", "COMMIT_MESSAGES", allow_squash_merge=False))

    assert result.resolution is None
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# GitHub retains the message setting while squash merging is disallowed, so a matching value is
# reported as inapplicable rather than as a success.
def test_SquashMergingDisallowedWithMatchingValue():
    result = _Evaluate(_Response("PR_TITLE", "COMMIT_MESSAGES", allow_squash_merge=False))

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
def test_MissingAllowSquashMerge(pat, expected_result):
    result = _Evaluate(
        {"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "COMMIT_MESSAGES"},
        pat=pat,
    )

    assert result.result == expected_result
    assert result.context is not None
    assert "squash commit message settings are not visible" in result.context


# ----------------------------------------------------------------------
def test_Skip():
    requirement = SquashCommitMessageRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"skip": True, "value": Values.PullRequestTitleAndCommitDetails},
    )

    assert result.result == EvaluateResultValue.Skipped
