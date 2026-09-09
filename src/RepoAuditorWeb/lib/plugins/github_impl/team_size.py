"""Contains the TeamSize enum."""

from enum import StrEnum


# ----------------------------------------------------------------------
class TeamSize(StrEnum):
    """The size of the team maintaining the repository. Solo (1 engineer), Small (2-5 engineers), or Large (6+ engineers)."""

    Solo = "solo"
    Small = "small"
    Large = "large"
