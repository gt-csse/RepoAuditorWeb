import textwrap

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast, override
from urllib.parse import quote, urlparse

from RepoAuditorWeb.lib.query import Query


# ----------------------------------------------------------------------
class ClonedRepositoryQuery(Query):
    """Query that clones the repository into `repo_dir` so that its requirements can inspect the repository's files."""

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        module_data["repo_dir"] = TemporaryDirectory()

        url = module_data["url"]
        assert isinstance(url, str), (url, type(url))

        pat = module_data["pat"]
        redacted_values: list[str] = []

        if pat is not None:
            assert isinstance(pat, str), (pat, type(pat))

            # Characters such as '@', '/', or ':' would otherwise change the host that is contacted.
            encoded_pat = quote(pat, safe="")
            redacted_values = [encoded_pat, pat]

            passed_url = urlparse(url)
            url = f"https://{encoded_pat}@{passed_url.netloc}{passed_url.path}"

        # Import git.Repo here so that it is only imported if a module that clones the repository is requested
        from git import Repo  # noqa: PLC0415

        try:
            Repo.clone_from(url, module_data["repo_dir"].name, branch=module_data["branch"], depth=1)
        except Exception as ex:
            # git output includes the clone url, which embeds the PAT.
            error = str(ex)
            for redacted_value in redacted_values:
                error = error.replace(redacted_value, "***")

            msg = textwrap.dedent(
                f"""\
                An error occurred while attempting to clone the target repository.

                If you are auditing a private repository, {
                    "please ensure your PAT has access to the repository."
                    if pat is not None
                    else "please provide a PAT with access to the repository."
                } A fine-grained PAT must grant the `Contents: Read` repository permission; a classic PAT must have the `repo` scope.

                Error: {error}
                """,
            )

            # The original exception is not chained when a PAT is present, as tracebacks would display the PAT within its message.
            raise RuntimeError(msg) from (ex if pat is None else None)

        return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        cast(TemporaryDirectory, query_data["repo_dir"]).cleanup()


# ----------------------------------------------------------------------
def GetRepositoryDirectory(query_data: dict[str, object]) -> Path:
    """Return the resolved directory of the repository cloned by ClonedRepositoryQuery."""

    return Path(cast(TemporaryDirectory, query_data["repo_dir"]).name).resolve()


# ----------------------------------------------------------------------
def IsWithinRepository(repo_dir: Path, path: Path) -> bool:
    """Return True if the path resolves within the repository.

    The repository is untrusted, so symlinks that escape it must be ignored; following them would
    reveal the contents of files on the host.
    """

    return path.resolve().is_relative_to(repo_dir.resolve())
