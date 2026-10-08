import textwrap

from typing import cast, override, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.shared.rationale_requirement import RationaleRequirement
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
# The licenses GitHub detects (https://choosealicense.com/appendix/) that are approved by the OSI
# (https://opensource.org/licenses), using the SPDX identifiers that GitHub reports.
OSI_APPROVED_LICENSES = frozenset(
    [
        "0BSD",
        "AFL-3.0",
        "AGPL-3.0",
        "Apache-2.0",
        "Artistic-2.0",
        "BlueOak-1.0.0",
        "BSD-2-Clause",
        "BSD-2-Clause-Patent",
        "BSD-3-Clause",
        "BSL-1.0",
        "CECILL-2.1",
        "ECL-2.0",
        "EPL-1.0",
        "EPL-2.0",
        "EUPL-1.1",
        "EUPL-1.2",
        "GPL-2.0",
        "GPL-3.0",
        "ISC",
        "LGPL-2.1",
        "LGPL-3.0",
        "LPPL-1.3c",
        "MIT",
        "MIT-0",
        "MPL-2.0",
        "MS-PL",
        "MS-RL",
        "MulanPSL-2.0",
        "NCSA",
        "OFL-1.1",
        "OSL-3.0",
        "PostgreSQL",
        "UPL-1.0",
        "Unlicense",
        "Zlib",
    ],
)


# ----------------------------------------------------------------------
class LicenseRequirement(RationaleRequirement):
    """Validates that GitHub detects an OSI-approved license in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "License",
            cast(str, self.__class__.__doc__),
            textwrap.dedent(
                """\
                The default behavior is to require that GitHub detects an OSI-approved license in the repository.

                ## Reasons for this Default

                - JOSS only publishes software that is open source as defined by the
                  [Open Source Initiative](https://opensource.org/osd), and its review checklist asks
                  whether the repository contains a plain-text LICENSE file with the contents of an
                  OSI-approved license.
                - GitHub's detection requires the license text to match a known license; a modified or
                  partial license is not identified, and reviewers may question whether it is open source.

                ## Reasons to Override this Default

                - The license is OSI-approved but is not one that GitHub detects, such as a license stored
                  in a `LICENSES` directory alongside others.
                """,
            ),
        )

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
        license_info = cast(dict, query_data["repository"]).get("license") or {}
        spdx_id = license_info.get("spdx_id")

        if spdx_id in OSI_APPROVED_LICENSES:
            return self._CreateResult(
                module,
                requirement_data,
                EvaluateResultValue.Success,
                f"GitHub detected the OSI-approved license `{spdx_id}`.",
            )

        if spdx_id is None:
            context = "GitHub did not detect a license in the repository."
        elif spdx_id == "NOASSERTION":
            context = "GitHub found a license file but could not identify the license within it."
        else:
            context = f"GitHub detected the license `{spdx_id}`, which is not approved by the OSI."

        return self._CreateResult(
            module,
            requirement_data,
            EvaluateResultValue.Error,
            context,
            textwrap.dedent(
                """\
                Add a LICENSE file to the root of the repository that contains the unmodified text of an
                [OSI-approved license](https://opensource.org/licenses), such as the
                [MIT License](https://choosealicense.com/licenses/mit/),
                [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/), or
                [GNU General Public License v3.0](https://choosealicense.com/licenses/gpl-3.0/).

                GitHub detects the license on the default branch, so the change must be merged there.
                """,
            ),
        )
