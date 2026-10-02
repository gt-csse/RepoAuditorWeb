from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Markdown, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class FileExistsRequirement(Requirement):
    """Requirement that checks if a file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        name: str,
        filename: str,
        directories: list[str],
        resolution: str,
        rationale: str,
        *,
        requires_explicit_include: bool = False,
        is_directory: bool = False,
    ) -> None:
        super().__init__(
            name,
            f"Validates that {filename} exists in the repository.",
            requires_explicit_include=requires_explicit_include,
        )

        self._filename = filename
        self._directories = list(directories)
        self._resolution = resolution
        self._rationale = rationale
        self._is_directory = is_directory

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "prohibit": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that the file does not exist."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        *,
        evaluate_all: bool,
    ) -> EvaluateResult:
        repo_dir = Path(cast(TemporaryDirectory, query_data["repo_dir"]).name)
        prohibit = cast(bool, requirement_data["prohibit"])

        found_locations: list[str] = []

        for directory in self._directories:
            this_dir = repo_dir / directory

            if not this_dir.is_dir():
                continue

            # follows GitHub's detection: case-insensitive, and files may have any extension (e.g. `readme.md`, `README`).
            found_locations.extend(
                item.relative_to(repo_dir).as_posix()
                for item in sorted(this_dir.glob("*"))
                if (
                    item.is_dir() and item.name.lower() == self._filename.lower()
                    if self._is_directory
                    else item.is_file() and item.name.split(".", 1)[0].lower() == self._filename.lower()
                )
            )

        if prohibit and found_locations:
            found_locations_str = ", ".join(f"`{location}`" for location in found_locations)

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"{self._filename} was found at {found_locations_str}, but the requirement was configured to prohibit it.",
                f"Remove {found_locations_str} from the repository.",
                self._CreateRationale(requirement_data),
                self,
                module,
            )

        if not prohibit and not found_locations:
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"{self._CreateNotFoundMessage()}.",
                self._resolution,
                self._CreateRationale(requirement_data),
                self,
                module,
            )

        if prohibit:
            context = f"{self._CreateNotFoundMessage()}, and the requirement was configured to prohibit it."
        else:
            found_locations_str = ", ".join(f"`{location}`" for location in found_locations)
            context = f"{self._filename} was found at {found_locations_str}."

        return EvaluateResult(
            EvaluateResultValue.Success,
            context,
            None,
            self._CreateRationale(requirement_data),
            self,
            module,
        )

    # ----------------------------------------------------------------------
    def _CreateNotFoundMessage(self) -> str:
        if len(self._directories) == 1:
            return f"{self._filename} was not found in the `{self._directories[0]}` directory"

        directories_str = ", ".join(f"`{directory}`" for directory in self._directories)

        return f"{self._filename} was not found in any of these directories: {directories_str}"

    # ----------------------------------------------------------------------
    def _CreateRationale(self, requirement_data: dict[str, object]) -> Markdown | None:
        return self._rationale if self.UsesDefaultValues(requirement_data) else None
