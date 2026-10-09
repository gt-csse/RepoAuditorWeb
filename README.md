**Project:**
[![License](https://img.shields.io/github/license/gt-csse/RepoAuditorWeb?color=dark-green)](https://github.com/gt-csse/RepoAuditorWeb/blob/main/LICENSE)

**Package:**
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/RepoAuditorWeb?color=dark-green)](https://pypi.org/project/RepoAuditorWeb/)
[![PyPI - Version](https://img.shields.io/pypi/v/RepoAuditorWeb?color=dark-green)](https://pypi.org/project/RepoAuditorWeb/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/RepoAuditorWeb)](https://pypistats.org/packages/repoauditorweb)

**Development:**
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![pytest](https://img.shields.io/badge/pytest-enabled-brightgreen)](https://docs.pytest.org/)
[![CI](https://github.com/gt-csse/RepoAuditorWeb/actions/workflows/CICD.yml/badge.svg)](https://github.com/gt-csse/RepoAuditorWeb/actions/workflows/CICD.yml)
[![Code Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/davidbrownell/2f9d770d13e3a148424f374f74d41f4b/raw/RepoAuditorWeb_code_coverage.json)](https://github.com/gt-csse/RepoAuditorWeb/actions)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/gt-csse/RepoAuditorWeb?color=dark-green)](https://github.com/gt-csse/RepoAuditorWeb/commits/main/)

<!-- Content above this delimiter will be copied to the generated README.md file. DO NOT REMOVE THIS COMMENT, as it will cause regeneration to fail. -->

## Contents
- [Overview](#overview)
- [Installation](#installation)
- [Development](#development)
- [Additional Information](#additional-information)
- [License](#license)

## Overview
`RepoAuditorWeb` audits GitHub repositories for best practices. Each requirement explains why it matters, and each failure includes step-by-step instructions for resolving it.

Requirements are grouped into modules:

| Module | Description | Requirements | Included by Default |
| --- | --- | --- | --- |
| `GitHub` | Repository settings, rulesets, and branch protection. | 43 | No |
| `CommunityStandards` | Files in GitHub's community profile checklist, such as `README`, `CODE_OF_CONDUCT`, `CONTRIBUTING`, `LICENSE`, `SECURITY`, issue templates, and pull request templates. | 7 | No |
| `ScientificSoftware` | Files expected of scientific software, such as `CITATION.cff`. | 1 | No |
| `JOSS` | Items in the [JOSS review checklist](https://joss.readthedocs.io/en/latest/review_checklist.html) that can be evaluated automatically, such as an OSI-approved license, public development history, contributors, documentation, tests, and the `paper.md` sections, metadata, length, and references. | 16 | No |

Every requirement has a default that can be customized or skipped, so the audit can be tailored to the conventions of a team or organization. Additional modules can be defined in separate packages; see [Custom Modules](https://github.com/gt-csse/RepoAuditorWeb/blob/main/docs/custom_modules.md).

### How to use `RepoAuditorWeb`
Run `repoauditorweb` to open the web experience, where modules and requirements are configured before the audit is executed:

```shell
uvx repoauditorweb --url https://github.com/<owner>/<repo> --GitHub-include --CommunityStandards-include
```

![Customizing the audit in the web experience](https://raw.githubusercontent.com/gt-csse/RepoAuditorWeb/main/docs/images/web_experience.png)

Click `Execute` to run the audit. The results summarize the outcome of each requirement and, for each failure, describe how to resolve it and the rationale behind the requirement's default:

![Results for a repository that does not satisfy the requirements](https://raw.githubusercontent.com/gt-csse/RepoAuditorWeb/main/docs/images/web_experience_results.png)

#### Experiences
Select the experience with `--experience`:

| Experience | Description |
| --- | --- |
| `web` (default) | Opens a window to configure and execute the audit. |
| `tui` | Configures and executes the audit within the terminal. |
| `console` | Executes the audit and writes the results to the terminal. |
| `json` | Executes the audit and writes the results to `stdout` as JSON; status information is written to `stderr`. |

`--execute` runs the audit immediately in the `web` and `tui` experiences.

#### JSON Output
The `json` experience writes a single document; `schema_version` is incremented whenever a change would break an existing consumer.

```json
{
  "schema_version": 1,
  "summary": {"skipped": 0, "does_not_apply": 0, "success": 0, "warning": 0, "error": 0, "total": 0},
  "results": [
    {
      "module": "<module name>",
      "requirement": "<requirement name>",
      "description": "<requirement description>",
      "result": "skipped | does_not_apply | success | warning | error",
      "context": "<Markdown or null>",
      "resolution": "<Markdown or null>",
      "rationale": "<Markdown or null>"
    }
  ]
}
```

Every result is included, not only failures. `resolution` and `rationale` are `null` when omitted via `--no-resolution` or `--no-rationale`.

#### Options
Every module and requirement contributes command line options; run `repoauditorweb --help` for the complete list. Common options include:

| Option | Description |
| --- | --- |
| `--url` | The GitHub repository to audit; applied to every included module. |
| `--pat` | A GitHub [Personal Access Token (PAT)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), or the path to a file containing one. Some requirements can only be evaluated with a PAT; see [PAT Permissions](#pat-permissions). |
| `--branch` | The branch to evaluate; the default branch is used if not specified. |
| `--<Module>-include` | Include a module in the audit. |
| `--<Module>-<Requirement>-skip` | Skip a requirement. |
| `--evaluate-all` | Evaluate requirements that would otherwise be suppressed because a parent setting is not enabled. |
| `--no-resolution`, `--no-rationale` | Omit resolutions or rationales from the results. |

`--url`, `--pat`, and `--branch` can also be provided through the environment variables `REPO_AUDITOR_WEB_GITHUB_URL`, `REPO_AUDITOR_WEB_GITHUB_PAT`, and `REPO_AUDITOR_WEB_GITHUB_BRANCH`.

#### PAT Permissions
A GitHub [Personal Access Token (PAT)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) is not required to audit public repositories, but GitHub only reports some settings to callers with elevated access. Requirements that cannot see a setting produce a warning without a PAT, and an error when the PAT lacks the necessary permissions.

| Module | Data | Fine-grained token permission | Repository role |
| --- | --- | --- | --- |
| `GitHub` | Repository, branch, and ruleset information | `Metadata: Read` | Read |
| `GitHub` | Merge, auto-merge, branch deletion, and commit message settings | `Contents: Read and write` | Write |
| `GitHub` | Secret protection, push protection, and Dependabot security updates | `Administration: Read` | Admin |
| `GitHub` | Classic branch protection rules | `Administration: Read` | Admin |
| `CommunityStandards`, `JOSS`, `ScientificSoftware` | Repository contents (private repositories only) | `Contents: Read` | Read |
| `JOSS` | Repository, commit, and contributor information | `Metadata: Read` | Read |

A fine-grained token must also list the audited repository among those it can access. A classic token requires the `repo` scope; the token's owner must still hold the repository role listed above.

#### Configuration Files
`--config` loads option values from a YAML file, so that an audit configuration can be stored and shared. Keys are the option names without the leading `--`, with `-` replaced by `_`. Values provided on the command line take precedence over values in the file.

```yaml
url: https://github.com/<owner>/<repo>
GitHub_include: true
GitHub_team_size: large
GitHub_DefaultBranch_value: [main, master]
CommunityStandards_include: true
```

```shell
uvx repoauditorweb --config audit.yaml
```

<!-- Content below this delimiter will be copied to the generated README.md file. DO NOT REMOVE THIS COMMENT, as it will cause regeneration to fail. -->

## Installation

| Installation Method | Command |
| --- | --- |
| Via [uv](https://github.com/astral-sh/uv) | `uv add RepoAuditorWeb` |
| Via [pip](https://pip.pypa.io/en/stable/) | `pip install RepoAuditorWeb` |

Installation is not necessary when using [uvx](https://docs.astral.sh/uv/guides/tools/), which downloads and runs `RepoAuditorWeb` in a temporary environment. Once installed, run `repoauditorweb` directly.

### Verifying Signed Artifacts
Artifacts are signed and verified using [py-minisign](https://github.com/x13a/py-minisign) and the public key in the file `./minisign_key.pub`.

To verify that an artifact is valid, visit [the latest release](https://github.com/gt-csse/RepoAuditorWeb/releases/latest) and download the `.minisign` signature file that corresponds to the artifact, then run the following command, replacing `<filename>` with the name of the artifact to be verified:

```shell
uv run --with py-minisign python -c "import minisign; minisign.PublicKey.from_file('minisign_key.pub').verify_file('<filename>'); print('The file has been verified.')"
```

## Development
Please visit [Contributing](https://github.com/gt-csse/RepoAuditorWeb/blob/main/CONTRIBUTING.md) and [Development](https://github.com/gt-csse/RepoAuditorWeb/blob/main/DEVELOPMENT.md) for information on contributing to this project.

## Additional Information
Additional information can be found at these locations.

| Title | Document | Description |
| --- | --- | --- |
| Code of Conduct | [CODE_OF_CONDUCT.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/CODE_OF_CONDUCT.md) | Information about the norms, rules, and responsibilities we adhere to when participating in this open source community. |
| Contributing | [CONTRIBUTING.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/CONTRIBUTING.md) | Information about contributing to this project. |
| Custom Modules | [docs/custom_modules.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/docs/custom_modules.md) | Information about defining custom modules in separate packages. |
| Development | [DEVELOPMENT.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/DEVELOPMENT.md) | Information about development activities involved in making changes to this project. |
| Governance | [GOVERNANCE.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/GOVERNANCE.md) | Information about how this project is governed. |
| Maintainers | [MAINTAINERS.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/MAINTAINERS.md) | Information about individuals who maintain this project. |
| Security | [SECURITY.md](https://github.com/gt-csse/RepoAuditorWeb/blob/main/SECURITY.md) | Information about how to privately report security issues associated with this project. |

## License
`RepoAuditorWeb` is licensed under the <a href="https://choosealicense.com/licenses/MIT/" target="_blank">MIT</a> license.
