import re

import pytest

from RepoAuditorWeb.lib.plugins.shared.repository_module import RepositoryModule


# ----------------------------------------------------------------------
def _CreateModule() -> RepositoryModule:
    return RepositoryModule("MyModule", "My description.", [])


# ----------------------------------------------------------------------
def _CreateArguments(**values) -> dict[str | None, dict[str, object]]:
    return {None: {"include": True, **values}}


# ----------------------------------------------------------------------
class TestConstruct:
    # ----------------------------------------------------------------------
    def test_Standard(self):
        module = _CreateModule()

        assert module.name == "MyModule"
        assert module.description == "My description."
        assert module.queries == []
        assert module.requires_explicit_include is True


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = _CreateModule().GetParameters()

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
        module_data = _CreateModule().GetModuleData(
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
        module_data = _CreateModule().GetModuleData(
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

        module_data = _CreateModule().GetModuleData(
            _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb", pat=str(pat_filename)),
        )

        assert module_data is not None
        assert module_data[None]["pat"] == "my_file_pat"

    # ----------------------------------------------------------------------
    def test_PreservesRequirementArguments(self):
        requirement_arguments: dict[str, object] = {"skip": False, "prohibit": False}

        arguments = _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb")
        arguments["Readme"] = requirement_arguments

        module_data = _CreateModule().GetModuleData(arguments)

        assert module_data is not None
        assert module_data["Readme"] is requirement_arguments

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("values", [{}, {"url": None}])
    def test_ErrorMissingUrl(self, values):
        with pytest.raises(ValueError, match=re.escape("'url' is a required argument for this module.")):
            _CreateModule().GetModuleData(_CreateArguments(**values))

    # ----------------------------------------------------------------------
    def test_ErrorWhitespacePat(self):
        with pytest.raises(
            ValueError, match=re.escape("'pat' must not be empty or contain only whitespace.")
        ):
            _CreateModule().GetModuleData(
                _CreateArguments(url="https://github.com/gt-csse/RepoAuditorWeb", pat="  "),
            )


# ----------------------------------------------------------------------
# The module data only holds resolved argument values, so there is nothing to release and the data must be left intact.
def test_CleanupModuleDataPreservesData():
    module_data: dict[str | None, dict[str, object]] = {
        None: {"url": "https://github.com/gt-csse/RepoAuditorWeb"}
    }

    _CreateModule().CleanupModuleData(module_data)

    assert module_data == {None: {"url": "https://github.com/gt-csse/RepoAuditorWeb"}}
