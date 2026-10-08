import textwrap

import pytest

from RepoAuditorWeb.lib.plugins.joss_impl.documents import (
    Document,
    FindPaper,
    FindReadme,
    GetHeadings,
    ReadText,
    StripCode,
)


# ----------------------------------------------------------------------
class TestGetHeadings:
    # ----------------------------------------------------------------------
    def test_Atx(self):
        text = textwrap.dedent(
            """\
            # Title
            Text
            ## Second ##
               ### Indented
            #NotAHeading
            # Using C#
            # ###
            """,
        )

        assert GetHeadings(text) == ["Title", "Second", "Indented", "Using C#"]

    # ----------------------------------------------------------------------
    def test_AtxWithTrailingWhitespace(self):
        assert GetHeadings("# a" + " " * 10000 + "b #  \n#   \n") == ["a" + " " * 10000 + "b"]

    # ----------------------------------------------------------------------
    def test_Setext(self):
        text = textwrap.dedent(
            """\
            Title
            =====

            Section
            -------

            Not a heading
            *************

            ---
            """,
        )

        assert GetHeadings(text) == ["Title", "Section"]

    # ----------------------------------------------------------------------
    def test_FrontMatter(self):
        assert GetHeadings("---\ntitle: Installation notes\n---\n# Title\n") == ["Title"]

    # ----------------------------------------------------------------------
    def test_ReStructuredText(self):
        text = textwrap.dedent(
            """\
            Title
            =====

            Installation
            ~~~~~~~~~~~~

            Use
            ```
            # Not a heading
            """,
        )

        assert GetHeadings(text, is_restructured_text=True) == ["Title", "Installation", "Use"]

    # ----------------------------------------------------------------------
    # A fence may directly follow a paragraph line that is no longer than the fence.
    def test_FenceAfterShortLine(self):
        text = textwrap.dedent(
            """\
            Use
            ```
            # Code
            ```

            # Installation
            """,
        )

        assert GetHeadings(text) == ["Installation"]

    # ----------------------------------------------------------------------
    def test_IgnoresFencedCode(self):
        text = textwrap.dedent(
            """\
            # Before
            ```python
            # Comment
            ~~~
            # Still code
            ```
            Text
            ===
            ~~~
            # Code
            ~~~
            # After
            """,
        )

        assert GetHeadings(text) == ["Before", "Text", "After"]

    # ----------------------------------------------------------------------
    def test_DocumentHeadings(self):
        assert Document("README.md", "# One\n## Two\n").headings == ["One", "Two"]

    # ----------------------------------------------------------------------
    def test_ReStructuredTextDocumentHeadings(self):
        assert Document("README.RST", "One\n~~~\n").headings == ["One"]


# ----------------------------------------------------------------------
def test_StripCode():
    text = textwrap.dedent(
        """\
        Cites @one and `@two`.
        ```
        @three
        ```
        Done.
        """,
    )

    assert StripCode(text) == "Cites @one and .\n\n\n\nDone."


# ----------------------------------------------------------------------
class TestFindReadme:
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("filename", ["README.md", "readme.rst", "README"])
    def test_Found(self, tmp_path, filename):
        (tmp_path / filename).write_text("# Title\n", encoding="utf-8")

        assert FindReadme(tmp_path) == Document(filename, "# Title\n")

    # ----------------------------------------------------------------------
    def test_NotFound(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "README.md").write_text("# Title\n", encoding="utf-8")
        (tmp_path / "README").mkdir()

        assert FindReadme(tmp_path) is None

    # ----------------------------------------------------------------------
    # Following symlinks out of the untrusted repository would reveal the contents of files on the host.
    def test_SymlinkOutsideRepository(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        (tmp_path / "README.md").write_text("# Title\n", encoding="utf-8")
        (repo_dir / "README.md").symlink_to(tmp_path / "README.md")

        assert FindReadme(repo_dir) is None


# ----------------------------------------------------------------------
class TestFindPaper:
    # ----------------------------------------------------------------------
    def test_NotFound(self, tmp_path):
        (tmp_path / "paper.txt").write_text("text", encoding="utf-8")

        assert FindPaper(tmp_path) is None

    # ----------------------------------------------------------------------
    def test_Shallowest(self, tmp_path):
        for directory in ["paper", "a/b", "joss"]:
            (tmp_path / directory).mkdir(parents=True)
            (tmp_path / directory / "paper.md").write_text(directory, encoding="utf-8")

        paper = FindPaper(tmp_path)

        assert paper is not None
        assert paper.path == "joss/paper.md"

    # ----------------------------------------------------------------------
    def test_IgnoresHiddenDirectories(self, tmp_path):
        (tmp_path / ".hidden").mkdir()
        (tmp_path / ".hidden" / "paper.md").write_text("text", encoding="utf-8")

        assert FindPaper(tmp_path) is None

    # ----------------------------------------------------------------------
    def test_SymlinkedFileOutsideRepository(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        (tmp_path / "paper.md").write_text("# Summary\n", encoding="utf-8")
        (repo_dir / "paper.md").symlink_to(tmp_path / "paper.md")

        assert FindPaper(repo_dir) is None

    # ----------------------------------------------------------------------
    def test_SymlinkedDirectoryOutsideRepository(self, tmp_path):
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()

        (tmp_path / "outside").mkdir()
        (tmp_path / "outside" / "paper.md").write_text("# Summary\n", encoding="utf-8")
        (repo_dir / "paper").symlink_to(tmp_path / "outside", target_is_directory=True)

        assert FindPaper(repo_dir) is None

    # ----------------------------------------------------------------------
    def test_Metadata(self, tmp_path):
        (tmp_path / "Paper.md").write_text(
            textwrap.dedent(
                """\
                ---
                title: My Title
                tags: [a, b]
                ---

                # Summary
                """,
            ),
            encoding="utf-8",
        )

        paper = FindPaper(tmp_path)

        assert paper is not None
        assert paper.path == "Paper.md"
        assert paper.metadata == {"title": "My Title", "tags": ["a", "b"]}
        assert paper.metadata_error is None
        assert paper.text == "\n# Summary\n"
        assert paper.headings == ["Summary"]

    # ----------------------------------------------------------------------
    def test_ByteOrderMark(self, tmp_path):
        (tmp_path / "paper.md").write_bytes(b"\xef\xbb\xbf---\ntitle: My Title\n---\n# Summary\n")

        paper = FindPaper(tmp_path)

        assert paper is not None
        assert paper.metadata == {"title": "My Title"}
        assert paper.text == "# Summary\n"

    # ----------------------------------------------------------------------
    def test_NoFrontMatter(self, tmp_path):
        (tmp_path / "paper.md").write_text("# Summary\n", encoding="utf-8")

        paper = FindPaper(tmp_path)

        assert paper is not None
        assert paper.metadata is None
        assert (
            paper.metadata_error
            == "The paper does not begin with YAML front matter delimited by `---` lines."
        )
        assert paper.text == "# Summary\n"

    # ----------------------------------------------------------------------
    def test_InvalidYaml(self, tmp_path):
        (tmp_path / "paper.md").write_text("---\ntitle: [unclosed\n---\n", encoding="utf-8")

        paper = FindPaper(tmp_path)

        assert paper is not None
        assert paper.metadata is None
        assert paper.metadata_error is not None
        assert paper.metadata_error.startswith("The paper's YAML front matter could not be parsed: ")

    # ----------------------------------------------------------------------
    def test_NotAMapping(self, tmp_path):
        (tmp_path / "paper.md").write_text("---\n- item\n...\n", encoding="utf-8")

        paper = FindPaper(tmp_path)

        assert paper is not None
        assert paper.metadata is None
        assert (
            paper.metadata_error == "The paper's YAML front matter is not a mapping of field names to values."
        )


# ----------------------------------------------------------------------
def test_ReadText(tmp_path):
    filename = tmp_path / "file.txt"
    filename.write_bytes(b"\xef\xbb\xbfText \xff\n")

    assert ReadText(filename) == "Text �\n"
