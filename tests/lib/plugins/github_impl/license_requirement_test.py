import pytest

from RepoAuditorWeb.lib.plugins.github_impl.license_requirement import LicenseRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue


# ----------------------------------------------------------------------
def _Evaluate(response: dict, acceptable_values: list[str] | None = None) -> EvaluateResult:
    return LicenseRequirement().Evaluate(
        {"response": response},
        {"skip": False, "value": ["MIT License"] if acceptable_values is None else acceptable_values},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = LicenseRequirement()

    assert requirement.name == "License"
    assert requirement.description == "Requirement to validate a repository's license."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = LicenseRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type == list[str]
    assert parameters["value"].default == ["MIT License"]


# ----------------------------------------------------------------------
def test_AcceptableLicense():
    result = _Evaluate({"license": {"name": "MIT License"}})

    assert result.result == EvaluateResultValue.Success
    assert result.context is None
    assert result.resolution is not None
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_AcceptableLicenseAmongMultiple():
    result = _Evaluate(
        {"license": {"name": "Apache License 2.0"}},
        ["MIT License", "Apache License 2.0"],
    )

    assert result.result == EvaluateResultValue.Success


# ----------------------------------------------------------------------
def test_UnacceptableLicense():
    result = _Evaluate({"license": {"name": "GPL-3.0"}})

    assert result.result == EvaluateResultValue.Error
    assert result.context == (
        "The license 'GPL-3.0' is not in the list of acceptable licenses ('MIT License')."
    )


# ----------------------------------------------------------------------
def test_UnacceptableLicenseListsAllAcceptableValues():
    result = _Evaluate({"license": {"name": "GPL-3.0"}}, ["MIT License", "Apache License 2.0"])

    assert result.context == (
        "The license 'GPL-3.0' is not in the list of acceptable licenses"
        " ('MIT License', 'Apache License 2.0')."
    )


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "response",
    [
        {},
        {"license": {}},
        {"license": {"name": None}},
    ],
)
def test_NoLicense(response):
    result = _Evaluate(response)

    assert result.result == EvaluateResultValue.Error
    assert result.context == "No license value was set."


# ----------------------------------------------------------------------
# GitHub reports an absent license as a null value rather than omitting the key, which is not a
# dictionary and therefore cannot be traversed.
def test_ErrorNullLicense():
    with pytest.raises(AttributeError):
        _Evaluate({"license": None})


# ----------------------------------------------------------------------
def test_EmptyAcceptableValues():
    result = _Evaluate({"license": {"name": "MIT License"}}, [])

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The license 'MIT License' is not in the list of acceptable licenses ()."


# ----------------------------------------------------------------------
def test_Skip():
    result = LicenseRequirement().Evaluate({}, {"skip": True, "value": ["MIT License"]})

    assert result.result == EvaluateResultValue.Skipped
