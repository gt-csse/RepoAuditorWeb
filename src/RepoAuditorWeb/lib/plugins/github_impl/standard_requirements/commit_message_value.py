"""Functionality shared by the requirements that validate a default commit message dropdown."""

import textwrap

from typing import cast, TYPE_CHECKING

from RepoAuditorWeb.lib.plugins.github_impl.standard_requirements.restricted_value import GetRestrictedValue
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue, Markdown, Requirement

if TYPE_CHECKING:
    from enum import StrEnum

    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.plugins.github_impl.module import GitHubSession


# ----------------------------------------------------------------------
# GitHub presents each of these settings as a single dropdown, but the API models it as a pair of
# fields whose values do not resemble the dropdown labels. Only the pairings in a requirement's map
# are reachable through the UI, so a repository reporting any other pairing was configured through
# the API.
type ApiValues = tuple[str, str]


# ----------------------------------------------------------------------
class CommitMessageSetting:
    """The data distinguishing one default commit message dropdown from another.

    The two dropdowns differ only in the values they offer, the fields they are reported in, and the
    merge method they belong to, so the evaluation itself is shared rather than duplicated.
    """

    # ----------------------------------------------------------------------
    def __init__(
        self,
        api_values: dict[StrEnum, ApiValues],
        ui_labels: dict[StrEnum, str],
        allow_key: str,
        title_key: str,
        message_key: str,
        method_description: str,
        method_availability_description: str,
        allow_checkbox_label: str,
        documentation_title: str,
        documentation_url: str,
    ) -> None:
        self.api_values = api_values
        self.ui_labels = ui_labels
        self.allow_key = allow_key
        self.title_key = title_key
        self.message_key = message_key
        self.method_description = method_description
        self.method_availability_description = method_availability_description
        self.allow_checkbox_label = allow_checkbox_label
        self.documentation_title = documentation_title
        self.documentation_url = documentation_url

        self.ui_labels_by_api_values: dict[ApiValues, str] = {
            values: ui_labels[value] for value, values in api_values.items()
        }

        # Sentence fragment naming the settings this dropdown reads, used by the shared helper to
        # describe what is not visible and to name the setting in failures.
        self.value_description = f"{method_description} message settings"

    # ----------------------------------------------------------------------
    def GetUILabel(self, title: object, message: object) -> str:
        """Return the quoted dropdown label for a pairing of the two API fields."""

        # A pairing that the dropdown cannot produce has no label to report, so the API values are
        # named directly rather than being forced onto the nearest option. The quoting is applied
        # here so that this case is not wrapped in quotes that suggest it is a label.
        label = self.ui_labels_by_api_values.get(cast(ApiValues, (title, message)))

        return f"'{label}'" if label is not None else f"title '{title}' with message '{message}'"


# ----------------------------------------------------------------------
def EvaluateCommitMessage(
    setting: CommitMessageSetting,
    value: StrEnum,
    rationale: Markdown,
    module: Module,
    requirement: Requirement,
    query_data: dict[str, object],
) -> EvaluateResult:
    """Compare the repository's dropdown pairing against the one 'value' names."""

    expected_title, expected_message = setting.api_values[value]

    # The dropdown configures the message GitHub pre-fills when a pull request is merged with this
    # method, so it has nothing to govern in a repository that disallows the method. The setting is
    # retained by GitHub while the checkbox is unchecked, which means an unrelated value here is
    # inert rather than a misconfiguration.
    allow_value = GetRestrictedValue(
        module,
        requirement,
        query_data,
        setting.allow_key,
        setting.value_description,
    )

    if isinstance(allow_value, EvaluateResult):
        return allow_value

    if not allow_value:
        return EvaluateResult(
            EvaluateResultValue.DoesNotApply,
            f"The repository does not allow {setting.method_availability_description}, so no default {setting.method_description} message is offered.",
            None,
            rationale,
            requirement,
            module,
        )

    # The two fields are reported together, so a single visibility check covers both.
    title_value = GetRestrictedValue(
        module,
        requirement,
        query_data,
        setting.title_key,
        setting.value_description,
    )

    if isinstance(title_value, EvaluateResult):
        return title_value

    message_value = GetRestrictedValue(
        module,
        requirement,
        query_data,
        setting.message_key,
        setting.value_description,
    )

    if isinstance(message_value, EvaluateResult):
        return message_value

    if title_value != expected_title or message_value != expected_message:
        repository_url = cast("GitHubSession", query_data["session"]).github_url

        resolution = textwrap.dedent(
            f"""\
            1) Open the repository's [General settings]({repository_url}/settings) page.
            2) Scroll to the **Pull Requests** section.
            3) Ensure that the **{setting.allow_checkbox_label}** checkbox is checked.
            4) Select **{setting.ui_labels[value]}** in the dropdown beneath it.

            See [{setting.documentation_title}]({setting.documentation_url})
            for more information.
            """,
        )

        # The dropdown label is reported rather than the API values, because the label is what the
        # user sees in the settings page and what the resolution asks them to select.
        return EvaluateResult(
            EvaluateResultValue.Error,
            f"The repository's default {setting.method_description} message is {setting.GetUILabel(title_value, message_value)}, but the requirement specifies it must be '{setting.ui_labels[value]}'.",
            resolution,
            rationale,
            requirement,
            module,
        )

    return EvaluateResult(EvaluateResultValue.Success, None, None, rationale, requirement, module)
