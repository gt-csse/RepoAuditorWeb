import inspect

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typer.models import OptionInfo


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class TyperParameter:
    """Representation of a parameter used in a function for Typer commands."""

    type: type
    default: object = inspect.Parameter.empty
    info: OptionInfo | None = None
