import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.license import LicenseRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_RESOLUTION = textwrap.dedent(
    """\
    Add a LICENSE file to the root of the repository. The file should contain the full text of the license under which the project is distributed, which defines how others may use, modify, and redistribute the code. Adopting an established open source license is a common approach; [choosealicense.com](https://choosealicense.com/) compares the most widely used options.

    GitHub provides these templates when adding a LICENSE file through its web interface, among others:

    - [MIT License](https://choosealicense.com/licenses/mit/)
    - [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/)
    - [GNU General Public License v3.0](https://choosealicense.com/licenses/gpl-3.0/)
    """,
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that a LICENSE file exists in the root of the repository.

    ## Reasons for this Default

    - Without a license, default copyright laws apply and others have no legal permission to
      use, modify, or distribute the code, even if the repository is public.
    - GitHub detects the license and displays it in the repository sidebar and search results,
      so users can determine the terms of use without reading the file.
    - Organizations frequently audit dependencies for license compatibility, and a project
      without a recognized license is often excluded from consideration.
    - GitHub's community profile checklist includes a LICENSE file, and its absence is
      visible to anyone evaluating the project's health.

    ## Reasons to Override this Default

    - The repository is proprietary or internal, and its terms of use are governed by an
      agreement outside of the repository.
    - The license is stored in a file GitHub recognizes but this requirement does not, such as
      `COPYING`, `LICENCE`, `UNLICENSE`, `LICENSE-MIT`, or files within a `LICENSES` directory.

    Note that this requirement only checks that a LICENSE file exists. It does not validate
    that GitHub is able to identify the license within it.
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
    requirement = LicenseRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": False},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = LicenseRequirement()

    assert requirement.name == "License"
    assert requirement.description == "Validates that LICENSE exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "filename",
    [
        "LICENSE",
        "LICENSE.md",
        "LICENSE.txt",
        "license.rst",
    ],
)
def test_Found(repo, filename):
    (Path(repo.name) / filename).write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Success
    assert result.context == f"LICENSE was found at `{filename}`."
    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
# Locations that GitHub does not search.
@pytest.mark.parametrize(
    "filename",
    [
        ".github/LICENSE.md",
        "docs/LICENSE.md",
    ],
)
def test_NotFound(repo, filename):
    filename = Path(repo.name) / filename

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")

    result = _Evaluate(repo)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "LICENSE was not found in the `.` directory."
    assert result.resolution == _RESOLUTION
    assert result.rationale == _RATIONALE
