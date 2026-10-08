import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.github_requirements.license import LicenseRequirement
from RepoAuditorWeb.lib.plugins.joss_impl.module import JOSSModule
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("license_info", "expected_result", "expected_context"),
    [
        (
            {"spdx_id": "MIT"},
            EvaluateResultValue.Success,
            "GitHub detected the OSI-approved license `MIT`.",
        ),
        (None, EvaluateResultValue.Error, "GitHub did not detect a license in the repository."),
        (
            {"spdx_id": "NOASSERTION"},
            EvaluateResultValue.Error,
            "GitHub found a license file but could not identify the license within it.",
        ),
        (
            {"spdx_id": "CC0-1.0"},
            EvaluateResultValue.Error,
            "GitHub detected the license `CC0-1.0`, which is not approved by the OSI.",
        ),
    ],
)
def test_Evaluate(license_info, expected_result, expected_context):
    result = LicenseRequirement().Evaluate(
        JOSSModule(), {"repository": {"license": license_info}}, {"skip": False}
    )

    assert result.result == expected_result
    assert result.context == expected_context
    assert (result.resolution is None) is (expected_result == EvaluateResultValue.Success)
    assert result.rationale is not None
