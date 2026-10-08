import re
import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.documents import Document
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.example_usage import (
    ExampleUsageRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.installation import (
    InstallationRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.statement_of_need import (
    StatementOfNeedRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("requirement_type", "heading"),
    [
        (StatementOfNeedRequirement, "Statement of Need"),
        (StatementOfNeedRequirement, "Why use this?"),
        (InstallationRequirement, "Installing"),
        (InstallationRequirement, "Setup"),
        (ExampleUsageRequirement, "Examples"),
        (ExampleUsageRequirement, "Quickstart"),
    ],
)
def test_Found(requirement_type, heading):
    requirement = requirement_type()

    result = requirement.Evaluate(
        JOSSModule(),
        {"readme": Document("README.md", f"# Title\n\n## {heading}\n")},
        {"skip": False, "pattern": requirement.GetParameters()["pattern"].default},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context is not None
    assert result.context.startswith(f"The `{heading}` heading in `README.md` matches `")
    assert result.resolution is None
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_NotFound():
    result = InstallationRequirement().Evaluate(
        JOSSModule(),
        {"readme": Document("README.rst", "Title\n=====\n\nWhy\n---\n")},
        {"skip": False, "pattern": "install"},
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == "No heading in `README.rst` matches `install`."
    assert result.resolution == textwrap.dedent(
        """\
        Add a section to `README.rst` describing how to install the software, with a heading that matches `install`.

        The section should list the software's dependencies and the steps required to install it,
        ideally using a package manager that installs the dependencies automatically.
        """,
    )
    assert result.rationale is None


# ----------------------------------------------------------------------
def test_FoundWithinHeading():
    result = InstallationRequirement().Evaluate(
        JOSSModule(),
        {"readme": Document("README.md", "# Title\n\n## Quick Install Guide\n")},
        {"skip": False, "pattern": "install"},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context == "The `Quick Install Guide` heading in `README.md` matches `install`."


# ----------------------------------------------------------------------
def test_InvalidPattern():
    with pytest.raises(re.error):
        InstallationRequirement().Evaluate(
            JOSSModule(),
            {"readme": Document("README.md", "# Title\n\n## Installation\n")},
            {"skip": False, "pattern": "(install"},
        )


# ----------------------------------------------------------------------
def test_NoReadme():
    requirement = ExampleUsageRequirement()

    result = requirement.Evaluate(
        JOSSModule(),
        {"readme": None},
        {"skip": False, "pattern": requirement.GetParameters()["pattern"].default},
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == "A README was not found in the root of the repository."
    assert result.resolution == textwrap.dedent(
        """\
        Add a README file to the root of the repository with a section describing how to use the software.

        The section should include examples that demonstrate how to use the software to solve
        real-world problems, ideally ones that readers can run and whose output they can compare.
        """,
    )
