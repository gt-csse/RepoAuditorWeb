"""Contains the TeamSize enum."""

from enum import StrEnum


# ----------------------------------------------------------------------
class TeamSize(StrEnum):
    """The size of the team maintaining the repository."""

    Solo = "solo"
    Small = "small"
    Large = "large"
