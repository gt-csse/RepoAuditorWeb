import re

import pytest

from RepoAuditorWeb.lib.plugins.community_standards_impl.module import CommunityStandardsModule


# ----------------------------------------------------------------------
# requires_explicit_include is expected to change, so the argument that enables the module is
# derived from the module rather than hard-coded.
def _CreateArguments(**values) -> dict[str | None, dict[str, object]]:
    module = CommunityStandardsModule()

    enable_argument = {"include": True} if module.requires_explicit_include else {"skip": False}

    return {None: {**enable_argument, **values}}


# ----------------------------------------------------------------------
def test_Construct():
    module = CommunityStandardsModule()

    assert module.name == "CommunityStandards"
    assert module.description == "Validates files that are considered community standards."
    assert [query.name for query in module.queries] == ["Community Standards"]


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = CommunityStandardsModule().GetParameters()

    assert list(parameters.keys())[1:] == ["url", "pat", "branch"]
    assert parameters["url"].type is str
    assert parameters["url"].default is None
    assert parameters["pat"].type == (str | None)
    assert parameters["pat"].default is None
    # The environment variable is bound once, by the common `--pat` option.
    assert parameters["pat"].info.envvar is None  # ty: ignore[unresolved-attribute]
    assert parameters["branch"].type == (str | None)
    assert parameters["branch"].default is None


# ----------------------------------------------------------------------
class TestGetModuleData:
    # ----------------------------------------------------------------------
    def test_ReplacesModuleArguments(self):
        module_data = CommunityStandardsModule().GetModuleData(
            _CreateArguments(
                url="https://github.com/gt-csse/RepoAuditorWeb",
                pat="my_pat",
                branch="my_branch",
            ),
        )

        assert module_data == {
            None: {
                "url": "https://github.com/gt-csse/RepoAuditorWeb",
                "pat": "my_pat",
                "branch": "my_branch",
            },
        }

    # ----------------------------------------------------------------------
    # pat and branch are optional, so their absence is not an error.
    def test_OptionalArgumentsAreAbsent(self):
        module_data = CommunityStandardsModule().GetModuleData(
            _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb"),
        )

        assert module_data == {
            None: {
                "url": "https://github.com/gt-csse/RepoAuditorWeb",
                "pat": None,
                "branch": None,
            },
        }

    # ----------------------------------------------------------------------
    # A PAT that names an existing file is read from that file, so tokens need not appear on the
    # command line.
    def test_PatFromFile(self, tmp_path):
        pat_filename = tmp_path / "pat.txt"
        pat_filename.write_text("  my_file_pat\n", encoding="utf-8")

        module_data = CommunityStandardsModule().GetModuleData(
            _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb", pat=str(pat_filename)),
        )

        assert module_data is not None
        assert module_data[None]["pat"] == "my_file_pat"

    # ----------------------------------------------------------------------
    def test_PreservesRequirementArguments(self):
        requirement_arguments: dict[str, object] = {"skip": False, "prohibit": False}

        arguments = _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb")
        arguments["Readme"] = requirement_arguments

        module_data = CommunityStandardsModule().GetModuleData(arguments)

        assert module_data is not None
        assert module_data["Readme"] is requirement_arguments

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("values", [{}, {"url": None}])
    def test_ErrorMissingUrl(self, values):
        with pytest.raises(ValueError, match=re.escape("'url' is a required argument for this module.")):
            CommunityStandardsModule().GetModuleData(_CreateArguments(**values))

    # ----------------------------------------------------------------------
    def test_ErrorWhitespacePat(self):
        with pytest.raises(
            ValueError, match=re.escape("'pat' must not be empty or contain only whitespace.")
        ):
            CommunityStandardsModule().GetModuleData(
                _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb", pat="  "),
            )
