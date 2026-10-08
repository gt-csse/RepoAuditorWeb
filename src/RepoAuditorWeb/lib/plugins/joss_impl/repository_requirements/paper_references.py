import posixpath
import re
import textwrap

from pathlib import PurePosixPath, PureWindowsPath
from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.joss_impl.documents import ReadText, StripCode
from RepoAuditorWeb.lib.plugins.joss_impl.repository_requirements.paper_content_requirement import (
    PaperContentRequirement,
)
from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import (
    GetRepositoryDirectory,
    IsWithinRepository,
)
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.joss_impl.documents import Paper


# ----------------------------------------------------------------------
# Pandoc citation keys begin with a letter, digit, or `_`, and may contain internal punctuation
# (https://pandoc.org/MANUAL.html#citation-syntax). The lookbehind excludes email addresses.
_CITATION_REGEX = re.compile(r"(?<![\w@])@\{?(?P<key>\w[\w:.#$%&\-+?<>~/]*)")
_KEY_TRAILING_PUNCTUATION = ":.#$%&-+?<>~/"

# The quantifiers are possessive, and keys exclude `@`, so that matching an untrusted file takes linear time.
_BIB_ENTRY_REGEX = re.compile(r"@(?P<type>\w++)\s*+[{(]\s*+(?P<key>[^,\s@]++)\s*+,")
_BIB_NON_ENTRY_TYPES = frozenset(["comment", "preamble", "string"])


# ----------------------------------------------------------------------
class PaperReferencesRequirement(PaperContentRequirement):
    """Validates that the paper cites references, and that each citation is defined in its bibliography."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PaperReferences",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require that the paper cites at least one reference and that
                every citation is defined in the bibliography.

                ## Reasons for this Default

                - JOSS requires a list of key references, including to other software addressing related
                  needs, and its review checklist asks whether the reference list is complete and uses
                  the proper citation syntax.
                - A citation that is not defined in the bibliography is rendered as `???` in the
                  compiled paper.

                ## Reasons to Override this Default

                - The software is not being prepared for submission to JOSS.
                """,
            ),
        )

    # ----------------------------------------------------------------------
    @override
    def _EvaluatePaper(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
        paper: Paper,
    ) -> EvaluateResult:
        repo_dir = GetRepositoryDirectory(query_data)

        bibliography = (paper.metadata or {}).get("bibliography")
        if not isinstance(bibliography, str) or not bibliography.strip():
            bibliography = "paper.bib"

        bibliography_path = (PurePosixPath(paper.path).parent / bibliography.strip()).as_posix()
        bibliography_fullpath = repo_dir / bibliography_path

        if (
            not _IsRelativePath(bibliography_path)
            or not bibliography_fullpath.is_file()
            or not IsWithinRepository(repo_dir, bibliography_fullpath)
        ):
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"The bibliography `{bibliography_path}` was not found.",
                textwrap.dedent(
                    f"""\
                    Add a BibTeX (or BibLaTeX) file at `{bibliography_path}` that defines each reference
                    cited in `{paper.path}`, or update the `bibliography` field in the paper's metadata to
                    name the existing file. Citation managers such as Zotero can export this format.
                    """,
                ),
            )

        defined_keys = {
            match.group("key")
            for match in _BIB_ENTRY_REGEX.finditer(ReadText(bibliography_fullpath))
            if match.group("type").lower() not in _BIB_NON_ENTRY_TYPES
        }

        cited_keys = list(
            dict.fromkeys(
                match.group("key").rstrip(_KEY_TRAILING_PUNCTUATION)
                for match in _CITATION_REGEX.finditer(StripCode(paper.text))
            ),
        )

        if not cited_keys:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"`{paper.path}` does not cite any references.",
                textwrap.dedent(
                    f"""\
                    Cite key references in `{paper.path}`, including other software that addresses related
                    needs, using their identifiers in `{bibliography_path}` (for example, `[@upper1974]`).
                    See [Citations](https://joss.readthedocs.io/en/latest/paper.html#citations) for more information.
                    """,
                ),
            )

        undefined_keys = [key for key in cited_keys if key not in defined_keys]

        if undefined_keys:
            undefined_str = ", ".join(f"`{key}`" for key in undefined_keys)

            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Error,
                f"`{paper.path}` cites references that are not defined in `{bibliography_path}`: {undefined_str}.",
                f"Add an entry for each undefined reference to `{bibliography_path}`, or correct the citation's identifier in `{paper.path}`.",
            )

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Success,
            f"`{paper.path}` cites {len(cited_keys)} reference(s), each of which is defined in `{bibliography_path}`.",
        )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _IsRelativePath(path: str) -> bool:
    # The path is untrusted, so it is validated before the filesystem is accessed; resolving an
    # absolute or UNC path would cause the host to access it (for example, by connecting to a share).
    normalized_path = posixpath.normpath(path.replace("\\", "/"))

    return not (
        normalized_path.startswith("/")
        or PureWindowsPath(normalized_path).drive
        or normalized_path.split("/", 1)[0] == ".."
    )
