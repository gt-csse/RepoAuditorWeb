import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_length import (
    PaperLengthRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_metadata import (
    PaperMetadataRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_references import (
    PaperReferencesRequirement,
)
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_sections import (
    PaperSectionsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("requirement_type", "requirement_data"),
    [
        (PaperMetadataRequirement, {}),
        (PaperSectionsRequirement, {"sections": ["Summary"]}),
        (PaperLengthRequirement, {"minimum": 750, "maximum": 1750}),
        (PaperReferencesRequirement, {}),
    ],
)
def test_DoesNotApply(requirement_type, requirement_data):
    result = requirement_type().Evaluate(JOSSModule(), {"paper": None}, {"skip": False, **requirement_data})

    assert result.result == EvaluateResultValue.DoesNotApply
    assert result.context == "`paper.md` was not found in the repository."
    assert result.resolution is None
