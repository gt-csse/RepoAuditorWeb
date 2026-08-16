"""Contains functionality useful when working with parameters and arguments."""

# ----------------------------------------------------------------------
#
# Terminology:
#   - Argument: A value passed to a function when it is called.
#   - Parameter: A variable in a function definition that receives an argument.
#
# ----------------------------------------------------------------------

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
