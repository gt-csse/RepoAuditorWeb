import textwrap

from RepoAuditorWeb.lib.plugins.community_standards_impl.requirements.impl.file_exists_requirement import (
    FileExistsRequirement,
)


# ----------------------------------------------------------------------
class SecurityRequirement(FileExistsRequirement):
    """Validates that a SECURITY file exists in the repository."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "Security",
            "SECURITY",
            # The directories GitHub searches.
            [".github", ".", "docs"],
            textwrap.dedent(
                """\
                Add a `SECURITY.md` file to the `.github` directory, the root of the repository, or the `docs` directory. The file should list the versions that receive security updates and explain how to privately report a vulnerability, such as through GitHub's private vulnerability reporting or a dedicated email address, along with the response timeline reporters can expect.

                See [Adding a security policy to your repository](https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository) for more information.
                """
            ),
            textwrap.dedent(
                """\
                The default behavior is to require that a SECURITY file exists in the repository.

                ## Reasons for this Default

                - Without documented instructions, reporters may disclose vulnerabilities in public
                  issues, exposing users before a fix is available.
                - GitHub links to the security policy from the repository's Security tab and when
                  contributors open an issue, so reporters can find it when it is needed.
                - Listing the supported versions tells users which releases receive security fixes and
                  when they must upgrade.
                - GitHub's community profile checklist includes a security policy, and its absence is
                  visible to anyone evaluating the project's health.

                ## Reasons to Override this Default

                - The organization provides a default SECURITY file in its `.github` repository.
                  GitHub displays that file for repositories that do not define their own, but this
                  requirement only inspects the repository itself and will not detect it.
                - The repository is not distributed or deployed, such as a personal, mirrored, or
                  archived repository, so there is no audience for a vulnerability disclosure process.
                """
            ),
        )
