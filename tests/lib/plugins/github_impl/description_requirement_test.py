import pytest

from RepoAuditorWeb.lib.plugins.github_impl.description_requirement import DescriptionRequirement, Values
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def _Evaluate(description: object, value: Values) -> EvaluateResultValue:
    return (
        DescriptionRequirement()
        .Evaluate({"response": {"description": description}}, {"skip": False, "value": value})
        .result
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = DescriptionRequirement()

    assert requirement.name == "Description"
    assert requirement.description == "Requirement to validate a repository's description."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = DescriptionRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "value"]
    assert parameters["value"].type is Values
    assert parameters["value"].default == Values.Populated


# ----------------------------------------------------------------------
def test_ValuesMembers():
    assert [(value.name, value.value) for value in Values] == [
        ("Populated", "populated"),
        ("AllowEmpty", "allow_empty"),
        ("Empty", "empty"),
    ]


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("My description.", EvaluateResultValue.Success),
        ("", EvaluateResultValue.Error),
        (None, EvaluateResultValue.Error),
    ],
)
def test_Populated(description, expected):
    assert _Evaluate(description, Values.Populated) == expected


# ----------------------------------------------------------------------
@pytest.mark.parametrize("description", ["My description.", "", None])
def test_AllowEmpty(description):
    assert _Evaluate(description, Values.AllowEmpty) == EvaluateResultValue.Success


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("My description.", EvaluateResultValue.Error),
        ("", EvaluateResultValue.Success),
        (None, EvaluateResultValue.Success),
    ],
)
def test_Empty(description, expected):
    assert _Evaluate(description, Values.Empty) == expected


# ----------------------------------------------------------------------
# The requirement reads 'description' via dict.get, so a response without the key is treated the
# same as an empty description.
def test_MissingDescriptionKey():
    result = DescriptionRequirement().Evaluate(
        {"response": {}},
        {"skip": False, "value": Values.Populated},
    )

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
def test_PopulatedFailureContext():
    result = DescriptionRequirement().Evaluate(
        {"response": {"description": ""}},
        {"skip": False, "value": Values.Populated},
    )

    assert result.context == "The repository description is empty."


# ----------------------------------------------------------------------
def test_EmptyFailureContext():
    result = DescriptionRequirement().Evaluate(
        {"response": {"description": "My description."}},
        {"skip": False, "value": Values.Empty},
    )

    assert result.context == "The repository description is populated."


# ----------------------------------------------------------------------
# AllowEmpty accepts any value, so it never reports context.
@pytest.mark.parametrize("description", ["My description.", "", None])
def test_AllowEmptyHasNoContext(description):
    result = DescriptionRequirement().Evaluate(
        {"response": {"description": description}},
        {"skip": False, "value": Values.AllowEmpty},
    )

    assert result.context is None


# ----------------------------------------------------------------------
def test_ResultAttributes():
    requirement = DescriptionRequirement()

    result = requirement.Evaluate(
        {"response": {"description": "My description."}},
        {"skip": False, "value": Values.Populated},
    )

    assert result.context is None
    assert result.resolution is None
    assert result.rationale is None
    assert result.requirement is requirement


# ----------------------------------------------------------------------
def test_Skip():
    result = DescriptionRequirement().Evaluate({}, {"skip": True, "value": Values.Populated})

    assert result.result == EvaluateResultValue.Skipped
