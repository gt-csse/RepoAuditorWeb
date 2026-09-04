import textwrap

from typing import cast, override, TYPE_CHECKING

from typer.models import OptionInfo

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.plugins.github_impl.restricted_value import GetRestrictedValue
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Requirement

if TYPE_CHECKING:
    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
class AutoMergeRequirement(Requirement):
    """Validates whether a pull request can be queued to merge once its requirements are met; the same reviews and status checks still apply."""

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__(
            "AutoMerge",
            cast(str, self.__class__.__doc__),
        )

    # ----------------------------------------------------------------------
    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return {
            # The default requires the setting to be enabled, so the parameter names the override
            # rather than the default; a 'require' parameter defaulting to True would be a flag that
            # is already on and cannot be turned off.
            "disallow": TyperParameter(
                bool,
                False,  # noqa: FBT003
                OptionInfo(help="Require that auto-merge is disabled."),
            ),
        }

    # ----------------------------------------------------------------------
    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        acceptable_value = not cast(bool, requirement_data["disallow"])

        rationale = textwrap.dedent(
            """\
            The default behavior is to require that auto-merge is enabled.

            Note that this differs from the state of a newly created repository, where the setting is
            disabled.

            ## Reasons for this Default

            - The setting relaxes nothing. Auto-merge merges only once every required review and
              status check has passed, which are the same conditions that gate the merge button, so
              a pull request that auto-merge lands is one that a person could have landed by hand at
              that moment. The branch protection rules and rulesets remain the authority over what
              may merge.
            - Without it, a pull request that has satisfied every requirement waits on someone
              noticing that it has. That delay is not a review of anything, since the review already
              happened, and the branch grows staler while it lasts.
            - Enabling it removes the incentive to sit on the merge button while checks run. Someone
              watching a long test suite so they can merge at the end is the case the setting exists
              to replace, and the alternative to it is a person merging from memory rather than from
              a signal.
            - The control is offered only on pull requests that cannot merge immediately, so it
              cannot be used to bypass a wait that does not exist, and only users with write access
              can enable it on a pull request.
            - Auto-merge disables itself when someone without write access pushes to the head branch
              or the base branch is changed, so a queued merge does not carry over to work that
              arrived after it was queued.
            - The setting only makes the control available. Each pull request still has to have
              auto-merge turned on individually, so enabling it here does not cause anything to merge
              on its own.

            ## Reasons to Override this Default

            - The project's merge requirements do not fully describe when a merge is acceptable, and
              a person is expected to apply judgment that no status check encodes. Auto-merge is only
              as trustworthy as the rules it waits on, so a repository whose rules are advisory
              should not offer it.
            - Merges are deliberately coordinated with something outside the repository, such as a
              release window or a deployment that a merge triggers, where landing a change as soon as
              it is ready is the wrong outcome.
            - The project requires signed commits and relies on the merge and squash methods, whose
              commits GitHub signs with its own web-flow key rather than the merging user's; a
              project that wants merges attributed to a human signature would rather they be
              performed by hand.

            Note that a repository using a merge queue does not need this setting, since the queue
            performs the merges itself once a pull request is added to it.
            """,
        )

        allow_auto_merge_value = GetRestrictedValue(
            module,
            self,
            query_data,
            "allow_auto_merge",
            "auto-merge settings",
        )

        if isinstance(allow_auto_merge_value, EvaluateResult):
            return allow_auto_merge_value

        if allow_auto_merge_value != acceptable_value:
            action = "Check" if acceptable_value else "Uncheck"

            repository_url = cast("GitHubSession", query_data["session"]).github_url

            resolution = textwrap.dedent(
                f"""\
                1) Open the repository's [General settings]({repository_url}/settings) page.
                2) Scroll to the **Pull Requests** section.
                3) {action} the **Allow auto-merge** checkbox.

                See [Managing auto-merge for pull requests in your repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository)
                for more information.
                """,
            )

            return EvaluateResult(
                EvaluateResultValue.Error,
                f"The repository's value is '{allow_auto_merge_value}', but the requirement specifies it must be '{acceptable_value}'.",
                resolution,
                rationale,
                self,
                module,
            )

        return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, self, module)
