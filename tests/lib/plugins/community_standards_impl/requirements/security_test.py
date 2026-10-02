import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.security import SecurityRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a `SECURITY.md` file to the `.github` directory, the root of the repository, or the `docs` directory. The file should list the versions that receive security updates and explain how to privately report a vulnerability, such as through GitHub's private vulnerability reporting or a dedicated email address, along with the response timeline reporters can expect.

    See [Adding a security policy to your repository](https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository) for more information.
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a SECURITY file exists in the repository.

    ## Reasons for this Default

    - Without documented instructions, reporters may disclose vulnerabilities in public
      issues, exposing users before a fix is available.
    - GitHub links to the security policy from the repository's Security tab and when
      contributors open an issue, so reporters can find it when it is needed.
    - Listing the supported versions tells users which releases receive security fixes and
      when they must upgrade.
    - GitHub's community profile checklist includes a security policy, and its absence is
      visible to anyone evaluating the project's health.

    ## Reasons to Override this Default

    - The organization provides a default SECURITY file in its `.github` repository.
      GitHub displays that file for repositories that do not define their own, but this
      requirement only inspects the repository itself and will not detect it.
    - The repository is not distributed or deployed, such as a personal, mirrored, or
      archived repository, so there is no audience for a vulnerability disclosure process.
    """,
)


# ----------------------------------------------------------------------
@pytest.fixture
def repo():
    repo_dir = TemporaryDirectory()

    yield repo_dir

    repo_dir.cleanup()


# ----------------------------------------------------------------------
def _Evaluate(repo: TemporaryDirectory) -> EvaluateResult:
    requirement = SecurityRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = SecurityRequirement()

    assert requirement.name == "Security"
    assert requirement.description == "Validates that SECURITY exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        ".github/SECURITY.md",
        "SECURITY.md",
        "security.md",
        "SECURITY",
        "docs/SECURITY.md",
    ],
)
def test_Found(repo, filename):
    location = filename
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Success
    assert result.context == f"SECURITY was found at `{location}`."
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        # Locations that GitHub does not search.
        "src/SECURITY.md",
        ".github/SECURITY/policy.md",
    ],
)
def test_NotFound(repo, filename):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "SECURITY was not found in any of these directories: `.github`, `.`, `docs`."
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
