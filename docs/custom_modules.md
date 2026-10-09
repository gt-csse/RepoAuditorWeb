# Custom Modules
`RepoAuditorWeb` discovers modules through [pluggy](https://pluggy.readthedocs.io/) plugins registered as Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/). A custom module can therefore live in a separate repository and package; once that package is installed in the same environment as `RepoAuditorWeb`, its module appears in every experience alongside the built-in modules.

## Contents
- [Concepts](#concepts)
- [Creating the Package](#creating-the-package)
- [Example: Validating Files](#example-validating-files)
- [Example: Custom Module, Query, and Requirement](#example-custom-module-query-and-requirement)
- [Naming Rules](#naming-rules)
- [Running the Audit](#running-the-audit)
- [Testing](#testing)

## Concepts

| Class | Location | Responsibility |
| --- | --- | --- |
| `Module` | `RepoAuditorWeb.lib.module` | A named collection of queries. Contributes module-level options (such as `--<Module>-url`) and converts command line arguments into data shared by its queries. |
| `Query` | `RepoAuditorWeb.lib.query` | Collects data (for example, by cloning the repository or calling the GitHub API) and cleans it up once its requirements have been evaluated. |
| `Requirement` | `RepoAuditorWeb.lib.requirement` | Evaluates a single best practice against the query data and returns an `EvaluateResult` with context, a resolution, and a rationale. |

A plugin is a Python module that implements the `GetModule` hook and returns a `Module`.

Reusable building blocks are available in `RepoAuditorWeb.lib.plugins.shared`:

| Class/Function | Description |
| --- | --- |
| `RepositoryModule` | Module that accepts `url`, `pat`, and `branch`, and requires `--<Module>-include`. |
| `ClonedRepositoryQuery` | Query that clones the repository and stores the directory in `query_data["repo_dir"]`. |
| `GetRepositoryDirectory`, `IsWithinRepository` | Return the cloned repository's directory, and determine whether a path (after resolving symlinks) is within it. |
| `RationaleRequirement` | Requirement that returns its rationale only when its default values are in use. |
| `FileExistsRequirement` | Requirement that validates that a file (or directory) exists in a cloned repository. |
| `GitHubSession` | `requests.Session` that sends requests relative to the repository's GitHub API url, with a default timeout and retries. |
| `GetRepositoryParameters`, `ResolveRepositoryArguments` | Declare and resolve the `url`, `pat`, and `branch` parameters for modules that do not clone the repository. |

## Creating the Package
Create a package that depends on `RepoAuditorWeb`:

```shell
uv init --package repoauditorweb-acme
cd repoauditorweb-acme
uv add repoauditorweb
```

Register each plugin in the `RepoAuditorWeb` entry point group (the group name is case-sensitive) in `pyproject.toml`:

```toml
[project.entry-points.RepoAuditorWeb]
AcmePythonPlugin = "AcmeAuditor.python_plugin"
AcmeTopicsPlugin = "AcmeAuditor.topics_plugin"
```

The examples below use this layout:

```
repoauditorweb-acme/
├── pyproject.toml
├── src/
│   └── AcmeAuditor/
│       ├── __init__.py
│       ├── python_plugin.py
│       └── topics_plugin.py
└── tests/
    └── topics_plugin_test.py
```

## Example: Validating Files
Modules that validate the presence of files can be assembled entirely from the shared building blocks. `FileExistsRequirement` matches names case-insensitively and ignores extensions, so `pyproject` matches `pyproject.toml`.

`src/AcmeAuditor/python_plugin.py`:

```python
import textwrap

import pluggy

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.shared.repository_module import RepositoryModule
from RepoAuditorWeb.lib.plugins.shared.cloned_repository_query import ClonedRepositoryQuery
from RepoAuditorWeb.lib.plugins.shared.file_exists_requirement import FileExistsRequirement


# ----------------------------------------------------------------------
class PyProjectRequirement(FileExistsRequirement):
    """Validates that a pyproject.toml file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "PyProject",
            "pyproject",  # Matched case-insensitively and without its extension
            ["."],
            textwrap.dedent(
                """\
                Add a `pyproject.toml` file to the root of the repository.

                See [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) for more information.
                """,
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a pyproject.toml file exists in the repository.

                ## Reasons for this Default

                - `pyproject.toml` is the standard location for Python project metadata and tool configuration.

                ## Reasons to Override this Default

                - The repository does not contain Python code.
                """,
            ),
        )


# ----------------------------------------------------------------------
@pluggy.HookimplMarker(APP_NAME)
def GetModule() -> Module:
    """Return the AcmePython module."""

    return RepositoryModule(
        "AcmePython",
        "Validates files expected in Acme's Python repositories.",
        [
            ClonedRepositoryQuery("Python", [PyProjectRequirement()]),
        ],
    )
```

This contributes `--AcmePython-include`, `--AcmePython-PyProject-skip`, and `--AcmePython-PyProject-prohibit`.

## Example: Custom Module, Query, and Requirement
Derive from the base classes directly when data comes from somewhere other than the repository's files. This module retrieves the repository's topics from the GitHub REST API and validates that a configurable minimum number of topics is present.

`src/AcmeAuditor/topics_plugin.py`:

```python
import textwrap

from dataclasses import asdict
from typing import cast, override
from urllib.parse import urlparse

import pluggy
import requests

from typer.models import OptionInfo

from RepoAuditorWeb import APP_NAME
from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.plugins.shared.repository_arguments import (
    GetRepositoryParameters,
    ResolveRepositoryArguments,
)
from RepoAuditorWeb.lib.query import Query
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement


# ----------------------------------------------------------------------
class MinimumTopicsRequirement(Requirement):
    """Validates that the repository is tagged with a minimum number of topics."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__("MinimumTopics", cast(str, self.__class__.__doc__))

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            "count": TyperParameter(
                int,
                3,
                OptionInfo(help="Minimum number of topics."),
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
        topics = cast(list[str], query_data["topics"])
        count = cast(int, requirement_data["count"])

        # The rationale justifies the default, so it is omitted once the default is overridden.
        rationale = (
            textwrap.dedent(
                """\
                The default behavior is to require at least 3 topics.

                ## Reasons for this Default

                - Topics allow the repository to be discovered through GitHub's topic pages and search.

                ## Reasons to Override this Default

                - The repository is not intended to be discovered.
                """,
            )
            if self.UsesDefaultValues(requirement_data)
            else None
        )

        if len(topics) < count:
            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository has {len(topics)} topic(s), but at least {count} are required.",
                "Add topics in the **About** section of the repository's home page.",
                rationale,
                self,
                module,
            )

        return EvaluateResult(
            EvaluateResultValue.Success,
            f"The repository has {len(topics)} topic(s).",
            None,
            rationale,
            self,
            module,
        )


# ----------------------------------------------------------------------
class TopicsQuery(Query):
    """Retrieves the repository's topics from the GitHub REST API."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__("Topics", [MinimumTopicsRequirement()])

    # ----------------------------------------------------------------------
    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        owner, repo = urlparse(cast(str, module_data["url"])).path.strip("/").split("/")[:2]

        headers = {"Accept": "application/vnd.github+json"}

        if module_data["pat"] is not None:
            headers["Authorization"] = f"Bearer {module_data['pat']}"

        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/topics",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        module_data["topics"] = response.json()["names"]

        return module_data

    # ----------------------------------------------------------------------
    @override
    def CleanupQueryData(self, query_data: dict[str, object]) -> None:
        pass


# ----------------------------------------------------------------------
class TopicsModule(Module):
    """Validates the repository's topics."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "AcmeTopics",
            cast(str, self.__class__.__doc__),
            [TopicsQuery()],
            requires_explicit_include=True,  # A url is required, so the module cannot run by default
        )

    # ----------------------------------------------------------------------
    @override
    def CleanupModuleData(self, module_data: dict[str | None, dict[str, object]]) -> None:
        pass

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        # Declaring 'url', 'pat', and 'branch' allows --url, --pat, and --branch to apply to this module.
        return GetRepositoryParameters()

    # ----------------------------------------------------------------------
    @override
    def _GetModuleDataImpl(
        self,
        arguments: dict[str | None, dict[str, object]],
    ) -> dict[str | None, dict[str, object]]:
        arguments[None] = asdict(ResolveRepositoryArguments(arguments.get(None, {})))

        return arguments


# ----------------------------------------------------------------------
@pluggy.HookimplMarker(APP_NAME)
def GetModule() -> Module:
    """Return the AcmeTopics module."""

    return TopicsModule()
```

Data flows through the classes as follows:

1. `Module.GetModuleData` receives the parsed arguments keyed by requirement name, where `None` holds the module's own parameters. Returning `None` skips the module.
2. `Query.GetQueryData` receives a copy of the module's `None` entry and returns the data passed to each requirement. Returning `None` skips the query.
3. `Requirement.Evaluate` receives the query data and the requirement's own arguments, including `skip` (or `include`).
4. `Query.CleanupQueryData` releases resources, such as temporary directories, after the query's requirements have been evaluated.
5. `Module.CleanupModuleData` releases resources shared by the module's queries, such as an HTTP session, after all of the module's queries have run. It is abstract, so every module must implement it, even if only with `pass`.

Guidelines for requirements:

- Keep the description to roughly 25 words or less.
- Author `context`, `resolution`, and `rationale` as Markdown; every experience renders it.
- Return a rationale only when `UsesDefaultValues` is `True`, as it justifies the defaults rather than an overridden configuration.
- Use `EvaluateResultValue.Warning` for conditions that limit the evaluation (such as a missing PAT), and `DoesNotApply` when the requirement is not relevant to the repository.

## Naming Rules
Command line options are generated from module, requirement, and parameter names (`--<Module>-<parameter>` and `--<Module>-<Requirement>-<parameter>`), so names are validated when `RepoAuditorWeb` starts:

- Module and requirement names must be valid Python identifiers without `_`.
- Parameter names must be valid Python identifiers and may contain `_`.
- Module names must be unique across all installed plugins; prefix custom modules (for example, `Acme`) to avoid collisions.
- Requirement names must be unique within a module.
- `include` and `skip` are reserved parameter names.

## Running the Audit
Install the package alongside `RepoAuditorWeb`:

```shell
uvx --with repoauditorweb-acme repoauditorweb --url https://github.com/<owner>/<repo> --AcmePython-include --AcmeTopics-include
```

During development, run from the package's repository, where `RepoAuditorWeb` is installed as a dependency:

```shell
uv run repoauditorweb --url https://github.com/<owner>/<repo> --AcmePython-include --AcmeTopics-include --AcmeTopics-MinimumTopics-count 5
```

To develop against a local clone of `RepoAuditorWeb`, add a source to the package's `pyproject.toml`:

```toml
[tool.uv.sources]
repoauditorweb = { path = "../RepoAuditorWeb", editable = true }
```

Custom modules can also be configured with `--config`, using keys such as `AcmeTopics_include` and `AcmeTopics_MinimumTopics_count`.

## Testing
Requirements can be evaluated directly with hand-crafted query data, which avoids network access in tests.

`tests/topics_plugin_test.py`:

```python
from AcmeAuditor.topics_plugin import MinimumTopicsRequirement, TopicsModule
from RepoAuditorWeb.lib.requirement import EvaluateResultValue


# ----------------------------------------------------------------------
def test_TooFewTopics():
    result = MinimumTopicsRequirement().Evaluate(
        TopicsModule(),
        {"topics": ["python"]},
        {"skip": False, "count": 3},
    )

    assert result.result == EvaluateResultValue.Error
    assert result.context == "The repository has 1 topic(s), but at least 3 are required."
    assert result.rationale is not None


# ----------------------------------------------------------------------
def test_OverriddenCount():
    result = MinimumTopicsRequirement().Evaluate(
        TopicsModule(),
        {"topics": ["python", "github"]},
        {"skip": False, "count": 2},
    )

    assert result.result == EvaluateResultValue.Success
    assert result.context == "The repository has 2 topic(s)."
    assert result.rationale is None
```

Run `uv run repoauditorweb --help` to confirm that the plugin is registered; its options appear alongside those of the built-in modules.
