import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.github_impl.license_requirement import LicenseRequirement
from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
_DOCUMENTATION_URL = (
    "https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features"
    "/customizing-your-repository/licensing-a-repository"
)


# ----------------------------------------------------------------------
_RATIONALE = textwrap.dedent(
    """\
    The default behavior is to require that the repository is licensed under the MIT License.

    ## Reasons for this Default

    - Without a license, default copyright law applies and the author retains all rights; no
      one may reproduce, distribute, or create derivative works from the code. Publishing a
      repository does not by itself grant anyone permission to use it.
    - The MIT License is short, permissive, and widely recognized, which minimizes the review
      burden on anyone deciding whether they may adopt the code.

    ## Reasons to Override this Default

    - The organization standardizes on a different license.
    - The repository incorporates code under a license that requires derived works to carry the
      same terms (for example, the GNU General Public License), which the MIT License cannot
      satisfy.
    - The project intends to require that modifications be shared, which a permissive license
      does not do.

    Note that GitHub identifies the license by comparing the `LICENSE` file against a list of
    known licenses, so an accurate copy of the chosen license is what causes it to be reported.
    """,
)


# ----------------------------------------------------------------------
def _CreateModule(requirement: LicenseRequirement) -> MyModule:
    return MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])


# ----------------------------------------------------------------------
def _Evaluate(
    response: dict,
    acceptable_values: list[str] | None = None,
    url: str = "https://github.com/gt-csse/RepoAuditorWeb",
) -> EvaluateResult:
    requirement = LicenseRequirement()

    return requirement.Evaluate(
        _CreateModule(requirement),
        {"response": response, "session": GitHubSession(url, None)},
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
    assert result.resolution is None


# ----------------------------------------------------------------------
# The rationale explains the default regardless of the outcome, so it is present on success even
# though there is nothing to resolve.
def test_SuccessRationale():
    result = _Evaluate({"license": {"name": "MIT License"}})

    assert result.rationale == _RATIONALE


# ----------------------------------------------------------------------
def test_ErrorRationale():
    result = _Evaluate({"license": {"name": "GPL-3.0"}})

    assert result.rationale == _RATIONALE


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
def test_UnacceptableLicenseResolution():
    result = _Evaluate({"license": {"name": "GPL-3.0"}})

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [home](https://github.com/gt-csse/RepoAuditorWeb) page.
        2) Add or replace the repository's `LICENSE` file with the text of one of these licenses: 'MIT License'.
        3) Commit the change to the repository's default branch.

        GitHub detects the license from the `LICENSE` file's contents, so the file must contain
        the license text verbatim.

        See [Licensing a repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# A missing license produces the same resolution as an unacceptable one, since both are fixed by
# committing an acceptable LICENSE file.
def test_NoLicenseResolution():
    result = _Evaluate({}, ["MIT License", "Apache License 2.0"])

    assert result.resolution == textwrap.dedent(
        f"""\
        1) Open the repository's [home](https://github.com/gt-csse/RepoAuditorWeb) page.
        2) Add or replace the repository's `LICENSE` file with the text of one of these licenses: 'MIT License', 'Apache License 2.0'.
        3) Commit the change to the repository's default branch.

        GitHub detects the license from the `LICENSE` file's contents, so the file must contain
        the license text verbatim.

        See [Licensing a repository]({_DOCUMENTATION_URL})
        for more information.
        """,
    )


# ----------------------------------------------------------------------
# The repository url is derived from the repository under audit rather than hard-coded, so it
# points at an Enterprise host when one is being audited.
def test_ResolutionUsesEnterpriseUrl():
    result = _Evaluate({"license": {"name": "GPL-3.0"}}, None, "https://github.example.com/o/r")

    assert result.resolution is not None
    assert "(https://github.example.com/o/r)" in result.resolution


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
    requirement = LicenseRequirement()

    result = requirement.Evaluate(_CreateModule(requirement), {}, {"skip": True, "value": ["MIT License"]})

    assert result.result == EvaluateResultValue.Skipped
