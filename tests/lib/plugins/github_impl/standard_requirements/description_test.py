import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.description import (
    DescriptionRequirement,
    Values,
)
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository has a description.

    ## Reasons for this Default

    - A repository search with no qualifier matches against the name, the description, and the
      topics, but not the contents of the README. An empty description therefore removes one of
      the three fields by which the repository can be found.
    - The description is what accompanies the repository in listings and search results, so it
      is what someone reads when deciding whether to open the repository at all.

    ## Reasons to Override this Default

    - The repository is not intended to be discovered, and describing its purpose in a field
      that feeds search works against that (`empty`).
    - The repository's name is self-explanatory, or the audience already knows what the
      repository is for, so requiring a description adds no value (`allow_empty`).
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: DescriptionRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _EvaluateResponse(
    response: dict,
    value: Values,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = DescriptionRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
        {"skip": False, "value": value},
    )


# ----------------------------------------------------------------------
def _Evaluate(description: object, value: Values) -> EvaluateResultValue:
    return _EvaluateResponse({"description": description}, value).result


# ----------------------------------------------------------------------
def test_Construct():
    requirement = DescriptionRequirement()

    assert requirement.name == "Description"
    assert (
        requirement.description
        == "Validates the repository's description, the About section text searched alongside the name and topics when no qualifier is given."
    )
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
    result = _EvaluateResponse({}, Values.Populated)

    assert result.result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
def test_PopulatedFailureContext():
    result = _EvaluateResponse({"description": ""}, Values.Populated)

    assert result.context == "The repository description is empty."


# ----------------------------------------------------------------------
def test_EmptyFailureContext():
    result = _EvaluateResponse({"description": "My description."}, Values.Empty)

    assert result.context == "The repository description is populated."


# ----------------------------------------------------------------------
# AllowEmpty accepts any value, so it never reports context.
@pytest.mark.parametrize("description", ["My description.", "", None])
def test_AllowEmptyHasNoContext(description):
    result = _EvaluateResponse({"description": description}, Values.AllowEmpty)

    assert result.context is None
    assert result.resolution is None


# ----------------------------------------------------------------------
def test_PopulatedFailureResolution():
    result = _EvaluateResponse({"description": ""}, Values.Populated)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [home](https://github.com/gt-csse/RepoAuditorWeb) page.
        2) Click the **Edit** button (or the gear icon) next to the **About** section.
        3) Enter a description in the **Description** text box.
        4) Click the **Save changes** button.

        See [About repositories]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The resolution directs the user to clear the description when it must be empty.
def test_EmptyFailureResolution():
    result = _EvaluateResponse({"description": "My description."}, Values.Empty)

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [home](https://github.com/gt-csse/RepoAuditorWeb) page.
        2) Click the **Edit** button (or the gear icon) next to the **About** section.
        3) Clear the contents of the **Description** text box.
        4) Click the **Save changes** button.

        See [About repositories]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The repository url is derived from the repository under audit rather than hard-coded, so it
# points at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _EvaluateResponse({"description": ""}, Values.Populated, "https://github.example.com/o/r")

    assert result.resolution is not None
    assert "(https://github.example.com/o/r)" in result.resolution


# ----------------------------------------------------------------------
def test_ResultAttributes():
    requirement = DescriptionRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {
            "response": {"description": "My description."},
            "session": GitHubSession("https://github.com/gt-csse/RepoAuditorWeb", None),
        },
        {"skip": False, "value": Values.Populated},
    )

    assert result.context is None
    assert result.resolution is None
    assert result.rationale == _RATIONALE
    assert result.requirement is requirement


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome or the selected value.
@pytest.mark.parametrize("value", list(Values))
def test_Rationale(value):
    result = _EvaluateResponse({"description": "My description."}, value)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _EvaluateResponse({"description": ""}, Values.Populated)

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_Skip():
    requirement = DescriptionRequirement()

    result = requirement.Evaluate(
        _CreateModule(requirement),
        {},
        {"skip": True, "value": Values.Populated},
    )

    assert result.result == EvaluateResultValue.Skipped
