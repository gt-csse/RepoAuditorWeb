"""Locates and parses the README and JOSS paper within a cloned repository."""

import os
import re

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import IsWithinRepository

if TYPE_CHECKING:
    from collections.abc import Iterator


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Document:
    """A Markdown (or reStructuredText) document within the repository."""

    path: str  # Relative to the repository root, using '/' as the separator
    text: str

    # ----------------------------------------------------------------------
    @cached_property
    def headings(self) -> list[str]:
        """Return the document's headings."""

        return GetHeadings(self.text, is_restructured_text=self.path.lower().endswith(".rst"))


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Paper(Document):
    """The JOSS paper; 'text' excludes the YAML front matter."""

    metadata: dict[str, object] | None
    metadata_error: str | None


# ----------------------------------------------------------------------
# The quantifier is possessive so that matching an untrusted line takes linear time.
_ATX_HEADING_REGEX = re.compile(r"^ {0,3}#{1,6}[ \t]++(?P<text>.*)")

_FRONT_MATTER_REGEX = re.compile(
    r"---[ \t]*\r?\n(?P<front_matter>.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|$)", re.DOTALL
)

_SETEXT_UNDERLINE_REGEX = re.compile(r"^ {0,3}([=\-])\1{2,}[ \t]*$")
_RESTRUCTURED_TEXT_UNDERLINE_REGEX = re.compile(r"^ {0,3}([=\-~^\"*+#`'.:_])\1{2,}[ \t]*$")

_FENCE_REGEX = re.compile(r"^ {0,3}(`{3,}|~{3,})")


# ----------------------------------------------------------------------
def GetHeadings(text: str, *, is_restructured_text: bool = False) -> list[str]:
    """Return the Markdown (ATX and setext) or reStructuredText headings, ignoring Markdown fenced code."""

    # The formats are parsed separately because a reStructuredText underline is indistinguishable
    # from a Markdown fence that interrupts a paragraph.
    if is_restructured_text:
        lines = text.splitlines()
        underline_regex = _RESTRUCTURED_TEXT_UNDERLINE_REGEX
    else:
        # The closing `---` of YAML front matter would otherwise form a setext heading.
        if match := _FRONT_MATTER_REGEX.match(text):
            text = text[match.end() :]

        lines = list(_IterateProseLines(text))
        underline_regex = _SETEXT_UNDERLINE_REGEX

    headings: list[str] = []
    previous_line = ""

    for line in lines:
        if not is_restructured_text and (match := _ATX_HEADING_REGEX.match(line)):
            if heading := _RemoveClosingSequence(match.group("text")):
                headings.append(heading)
        elif previous_line.strip() and underline_regex.match(line):
            headings.append(previous_line.strip())

        previous_line = line

    return headings


# ----------------------------------------------------------------------
def StripCode(text: str) -> str:
    """Remove fenced code blocks and inline code, which may contain text that resembles citations."""

    return re.sub(r"`[^`\n]*`", "", "\n".join(_IterateProseLines(text)))


# ----------------------------------------------------------------------
def FindReadme(repo_dir: Path) -> Document | None:
    """Return the README in the root of the repository, matched as GitHub does: case-insensitively and with any extension."""

    for item in sorted(repo_dir.iterdir()):
        if item.name.split(".", 1)[0].lower() == "readme" and _IsSafeFile(repo_dir, item):
            return Document(item.relative_to(repo_dir).as_posix(), ReadText(item))

    return None


# ----------------------------------------------------------------------
def FindPaper(repo_dir: Path) -> Paper | None:
    """Return the shallowest `paper.md` in the repository, as JOSS does not prescribe its location."""

    candidates: list[Path] = []

    # os.walk does not follow symlinked directories, which could otherwise escape the repository.
    for root, directories, filenames in os.walk(repo_dir):
        directories[:] = [directory for directory in directories if not directory.startswith(".")]

        candidates.extend(
            Path(root) / filename
            for filename in filenames
            if filename.lower() == "paper.md" and _IsSafeFile(repo_dir, Path(root) / filename)
        )

    if not candidates:
        return None

    path = min(candidates, key=lambda candidate: (len(candidate.parts), candidate.as_posix()))
    text = ReadText(path)

    metadata: dict[str, object] | None = None
    metadata_error: str | None = None

    match = _FRONT_MATTER_REGEX.match(text)

    if match is None:
        metadata_error = "The paper does not begin with YAML front matter delimited by `---` lines."
    else:
        text = text[match.end() :]

        try:
            content = yaml.safe_load(match.group("front_matter"))
        except yaml.YAMLError as ex:
            metadata_error = f"The paper's YAML front matter could not be parsed: {ex}"
        else:
            if isinstance(content, dict):
                metadata = content
            else:
                metadata_error = "The paper's YAML front matter is not a mapping of field names to values."

    return Paper(path.relative_to(repo_dir).as_posix(), text, metadata, metadata_error)


# ----------------------------------------------------------------------
def ReadText(path: Path) -> str:
    """Read an untrusted text file, ignoring a byte order mark that would prevent matching at the start of the text."""

    return path.read_text(encoding="utf-8-sig", errors="replace")


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _IterateProseLines(text: str) -> Iterator[str]:
    # Fence and code lines are replaced by empty lines so that line-relative constructs, such as
    # setext headings, are not formed across a code block.
    fence: str | None = None

    for line in text.splitlines():
        if fence_match := _FENCE_REGEX.match(line):
            marker = fence_match.group(1)[0]

            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None

            yield ""
        else:
            yield "" if fence is not None else line


# ----------------------------------------------------------------------
def _RemoveClosingSequence(text: str) -> str:
    text = text.rstrip(" \t")
    without_closing = text.rstrip("#")

    # A closing sequence must be preceded by whitespace, so that headings such as `C#` are preserved.
    if not without_closing or without_closing[-1] in " \t":
        text = without_closing.rstrip(" \t")

    return text


# ----------------------------------------------------------------------
def _IsSafeFile(repo_dir: Path, path: Path) -> bool:
    return path.is_file() and IsWithinRepository(repo_dir, path)
