import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.plugins.github_impl.support_discussions_requirement import (
    SupportDiscussionsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/enabling-or-disabling-github-discussions-for-a-repository"


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository's discussions are disabled, which
    matches the state of a newly created repository.

    ## Reasons for this Default

    - Discussions are a second inbound channel that overlaps the issue tracker, so a project
      running both must triage two queues and decide for each incoming report which one it
      belongs in. A project that has not committed to that moderation effort is better served
      by the single queue it already has.
    - Discussions have no state to close and no cross-referencing role: they are not the target
      of `Fixes #<number>`, they do not appear in a milestone, and they cannot be added to a
      project board the way an issue can. Work that needs to be tracked has to be re-filed as
      an issue anyway.
    - Discussions are a search surface distinct from issues, so a contributor searching for a
      previously answered question finds it only if they search the surface it was answered on.
      Splitting a project's history across both makes prior answers harder to find.
    - Enabling the feature without seeding categories or answering anything presents
      contributors with an empty forum, which reads as an unmaintained support channel rather
      than an invitation.
    - The feature is unnecessary for a repository whose audience is its own maintainers, since
      the conversation it hosts is already happening in pull request review.

    ## Reasons to Override this Default

    - The project receives support questions that are not defects, which is the case GitHub
      gives for the feature. Routing them to discussions keeps the issue tracker limited to
      actionable work, and a question-and-answer category lets the accepted response be marked
      as the answer so later readers find it.
    - The project wants to gather community input on direction before committing to work, which
      discussions support through polls, announcements, and upvoting in a format that does not
      require every thread to resolve.
    - Discussions replace a chat service or mailing list that the project would otherwise depend
      on, keeping the conversation on the same host as the code and visible to anyone with
      repository access.

    Note that enabling discussions does not by itself route questions away from the issue
    tracker; a `contact_links` entry in `.github/ISSUE_TEMPLATE/config.yml` is what presents
    discussions as the destination when a contributor starts to open an issue. Also note that
    an organization's discussions are hosted by a source repository, so this setting may be
    enabled on a repository to serve the organization rather than the repository itself.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: SupportDiscussionsRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    *,
    require: bool = False,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = SupportDiscussionsRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "require": require},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SupportDiscussionsRequirement()

    assert requirement.name == "SupportDiscussions"
    assert (
        requirement.description
        == "Validates whether the repository's discussions are enabled; discussions are a forum for questions and open-ended conversation that is separate from the issue tracker."
    )
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = SupportDiscussionsRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "require"]
    assert parameters["require"].type is bool
    assert parameters["require"].default is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("has_discussions", "require"),
    [(False, False), (True, True)],
)
def test_MatchingStatus(has_discussions, require):
    result = _Evaluate({"has_discussions": has_discussions}, require=require)

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"has_discussions": False})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"has_discussions": True})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorResolution():
    result = _Evaluate({"has_discussions": True})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Uncheck the **Discussions** checkbox.

        See [Enabling or disabling GitHub Discussions for a repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to check the setting when discussions must be enabled.
def test_ErrorResolutionWhenRequired():
    result = _Evaluate({"has_discussions": False}, require=True)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [General settings](https://github.com/gt-csse/RepoAuditorWeb/settings) page.
        2) Scroll to the **Features** section.
        3) Check the **Discussions** checkbox.

        See [Enabling or disabling GitHub Discussions for a repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The settings url is derived from the repository under audit rather than hard-coded, so it points
# at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"has_discussions": True}, url="https://github.example.com/my-org/my-repo")

    assert result.resolution is not None
    assert "(https://github.example.com/my-org/my-repo/settings)" in result.resolution


# ----------------------------------------------------------------------
def test_DiscussionsWhenDisallowed():
    result = _Evaluate({"has_discussions": True})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'True', but the requirement specifies it must be 'False'."
    )


# ----------------------------------------------------------------------
def test_NoDiscussionsWhenRequired():
    result = _Evaluate({"has_discussions": False}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
# An absent 'has_discussions' key is treated as False, which satisfies the default requirement.
def test_MissingStatus():
    result = _Evaluate({})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None


# ----------------------------------------------------------------------
def test_MissingStatusWhenRequired():
    result = _Evaluate({}, require=True)

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The repository's value is 'False', but the requirement specifies it must be 'True'."
    )


# ----------------------------------------------------------------------
def test_Skip():
    requirement = SupportDiscussionsRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "require": False})

    assert result.result == EvaluateResultValue.Skipped
