from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import (
    FileExistsRequirement,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import MyModule, MyQuery


# ----------------------------------------------------------------------
def _CreateRequirement(*, requires_explicit_include: bool = False) -> FileExistsRequirement:
    return FileExistsRequirement(
        "MyFile",
        "MY_FILE",
        [".", "docs"],
        "My resolution.",
        "My rationale.",
        requires_explicit_include=requires_explicit_include,
    )


# ----------------------------------------------------------------------
# The query provides the cloned repository as a TemporaryDirectory, so the tests do the same.
@pytest.fixture
def repo():
    repo_dir = TemporaryDirectory()

    yield repo_dir

    repo_dir.cleanup()


# ----------------------------------------------------------------------
def _CreateFile(repo: TemporaryDirectory, relative_path: str) -> None:
    filename = Path(repo.name) / relative_path

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text("content", encoding="utf-8")


# ----------------------------------------------------------------------
def _Evaluate(
    repo: TemporaryDirectory,
    *,
    prohibit: bool = False,
    requirement: FileExistsRequirement | None = None,
) -> EvaluateResult:
    requirement = requirement or _CreateRequirement()

    return requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {"repo_dir": repo},
        {"skip": False, "prohibit": prohibit},
    )


# ----------------------------------------------------------------------
def test_Construct():
    requirement = _CreateRequirement()

    assert requirement.name == "MyFile"
    assert requirement.description == "Validates that MY_FILE exists in the repository."
    assert requirement.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_ConstructRequiresExplicitInclude():
    assert _CreateRequirement(requires_explicit_include=True).requires_explicit_include is True


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = _CreateRequirement().GetParameters()

    assert list(parameters.keys()) == ["skip", "prohibit"]
    assert parameters["prohibit"].type is bool
    assert parameters["prohibit"].default is False


# ----------------------------------------------------------------------
class TestRequired:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize(
        "location",
        ["MY_FILE.md", "docs/MY_FILE.md", "my_file.md", "My_File.rst", "MY_FILE", "MY_FILE.zh-CN.md"],
    )
    def test_Found(self, repo, location):
        _CreateFile(repo, location)

        result = _Evaluate(repo)

        assert result.result == EvaluateResultValue.Success
        assert result.context == f"MY_FILE was found at `{location}`."
        assert result.resolution is None
        assert result.rationale == "My rationale."

    # ----------------------------------------------------------------------
    def test_NotFound(self, repo):
        result = _Evaluate(repo)

        assert result.result == EvaluateResultValue.Error
        assert result.context == "MY_FILE was not found in any of these directories: `.`, `docs`."
        assert result.resolution == "My resolution."
        assert result.rationale == "My rationale."

    # ----------------------------------------------------------------------
    def test_NotFoundSingleDirectory(self, repo):
        requirement = FileExistsRequirement("MyFile", "MY_FILE", ["docs"], "My resolution.", "My rationale.")

        result = _Evaluate(repo, requirement=requirement)

        assert result.result == EvaluateResultValue.Error
        assert result.context == "MY_FILE was not found in the `docs` directory."

    # ----------------------------------------------------------------------
    # Only the listed directories are searched, so a file elsewhere in the repository does not count.
    def test_UnlistedLocation(self, repo):
        _CreateFile(repo, "other/MY_FILE.md")

        assert _Evaluate(repo).result == EvaluateResultValue.Error

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("location", ["MY_FILE_OTHER.md", "OTHER_MY_FILE.md"])
    def test_SimilarNameIsNotAMatch(self, repo, location):
        _CreateFile(repo, location)

        assert _Evaluate(repo).result == EvaluateResultValue.Error

    # ----------------------------------------------------------------------
    def test_DirectoryIsNotAFile(self, repo):
        (Path(repo.name) / "MY_FILE.md").mkdir()

        assert _Evaluate(repo).result == EvaluateResultValue.Error

    # ----------------------------------------------------------------------
    def test_SymlinkWithinRepository(self, repo):
        _CreateFile(repo, "other/MY_FILE.md")
        (Path(repo.name) / "MY_FILE.md").symlink_to(Path(repo.name) / "other" / "MY_FILE.md")

        result = _Evaluate(repo)

        assert result.result == EvaluateResultValue.Success
        assert result.context == "MY_FILE was found at `MY_FILE.md`."

    # ----------------------------------------------------------------------
    # Following symlinks out of the untrusted repository would reveal whether paths on the host exist.
    def test_SymlinkedFileOutsideRepository(self, repo, tmp_path):
        (tmp_path / "MY_FILE.md").write_text("content", encoding="utf-8")
        (Path(repo.name) / "MY_FILE.md").symlink_to(tmp_path / "MY_FILE.md")

        assert _Evaluate(repo).result == EvaluateResultValue.Error

    # ----------------------------------------------------------------------
    # The file links back into the repository so that only the directory check can reject it.
    def test_SymlinkedDirectoryOutsideRepository(self, repo, tmp_path):
        _CreateFile(repo, "other/MY_FILE.md")
        (tmp_path / "MY_FILE.md").symlink_to(Path(repo.name) / "other" / "MY_FILE.md")
        (Path(repo.name) / "docs").symlink_to(tmp_path, target_is_directory=True)

        assert _Evaluate(repo).result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
class TestIsDirectory:
    # ----------------------------------------------------------------------
    @staticmethod
    def _CreateDirectoryRequirement() -> FileExistsRequirement:
        return FileExistsRequirement(
            "MyDir",
            "MY_DIR",
            [".", "docs"],
            "My resolution.",
            "My rationale.",
            is_directory=True,
        )

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("location", ["MY_DIR", "docs/my_dir"])
    def test_Found(self, repo, location):
        _CreateFile(repo, f"{location}/template.md")

        result = _Evaluate(repo, requirement=self._CreateDirectoryRequirement())

        assert result.result == EvaluateResultValue.Success
        assert result.context == f"MY_DIR was found at `{location}`."

    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("location", ["MY_DIR", "MY_DIR.md"])
    def test_FileIsNotADirectory(self, repo, location):
        _CreateFile(repo, location)

        assert (
            _Evaluate(repo, requirement=self._CreateDirectoryRequirement()).result
            == EvaluateResultValue.Error
        )

    # ----------------------------------------------------------------------
    # Extensions are only ignored for files, so a directory must match the name exactly.
    def test_DirectoryWithExtensionIsNotAMatch(self, repo):
        _CreateFile(repo, "MY_DIR.old/template.md")

        assert (
            _Evaluate(repo, requirement=self._CreateDirectoryRequirement()).result
            == EvaluateResultValue.Error
        )


# ----------------------------------------------------------------------
class TestProhibited:
    # ----------------------------------------------------------------------
    def test_NotFound(self, repo):
        result = _Evaluate(repo, prohibit=True)

        assert result.result == EvaluateResultValue.Success
        assert result.context == (
            "MY_FILE was not found in any of these directories: `.`, `docs`, and the requirement was configured to prohibit it."
        )
        assert result.resolution is None
        assert result.rationale is None

    # ----------------------------------------------------------------------
    def test_NotFoundSingleDirectory(self, repo):
        requirement = FileExistsRequirement("MyFile", "MY_FILE", ["docs"], "My resolution.", "My rationale.")

        result = _Evaluate(repo, prohibit=True, requirement=requirement)

        assert result.result == EvaluateResultValue.Success
        assert result.context == (
            "MY_FILE was not found in the `docs` directory, and the requirement was configured to prohibit it."
        )

    # ----------------------------------------------------------------------
    # The rationale justifies the default (required), so it does not apply once prohibit overrides it.
    def test_Found(self, repo):
        _CreateFile(repo, "docs/MY_FILE.md")

        result = _Evaluate(repo, prohibit=True)

        assert result.result == EvaluateResultValue.Error
        assert (
            result.context
            == "MY_FILE was found at `docs/MY_FILE.md`, but the requirement was configured to prohibit it."
        )
        assert result.resolution == "Remove `docs/MY_FILE.md` from the repository."
        assert result.rationale is None

    # ----------------------------------------------------------------------
    # Every offending location is reported so that all of them can be removed in a single pass.
    def test_FoundInMultipleLocations(self, repo):
        _CreateFile(repo, "MY_FILE.md")
        _CreateFile(repo, "docs/MY_FILE.md")

        result = _Evaluate(repo, prohibit=True)

        assert result.result == EvaluateResultValue.Error
        assert (
            result.context
            == "MY_FILE was found at `MY_FILE.md`, `docs/MY_FILE.md`, but the requirement was configured to prohibit it."
        )
        assert result.resolution == "Remove `MY_FILE.md`, `docs/MY_FILE.md` from the repository."


# ----------------------------------------------------------------------
def test_ResultAttributes(repo):
    requirement = _CreateRequirement()
    module = MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])])

    result = requirement.Evaluate(module, {"repo_dir": repo}, {"skip": False, "prohibit": False})

    assert result.requirement is requirement
    assert result.module is module


# ----------------------------------------------------------------------
# The constructor copies the directories, so later changes to the caller's list have no effect.
def test_DirectoriesAreCopied(repo):
    directories = ["."]

    requirement = FileExistsRequirement("MyFile", "MY_FILE", directories, "My resolution.", "My rationale.")
    directories.append("docs")

    _CreateFile(repo, "docs/MY_FILE.md")

    assert _Evaluate(repo, requirement=requirement).result == EvaluateResultValue.Error


# ----------------------------------------------------------------------
def test_Skip():
    requirement = _CreateRequirement()

    result = requirement.Evaluate(
        MyModule("MyModule", "My description.", [MyQuery("MyQuery", [requirement])]),
        {},
        {"skip": True, "prohibit": False},
    )

    assert result.result == EvaluateResultValue.Skipped
