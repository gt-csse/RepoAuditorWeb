"""Contains functionality useful when working with parameters and arguments."""

# ----------------------------------------------------------------------
#
# Terminology:
#   - Argument: A value passed to a function when it is called.
#   - Parameter: A variable in a function definition that receives an argument.
#
# ----------------------------------------------------------------------

import inspect
import keyword

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typer.models import OptionInfo

    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
# |
# |  Public Types
# |
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class TyperParameter:
    """Representation of a parameter used in a function for Typer commands."""

    type: type
    default: object = inspect.Parameter.empty
    info: OptionInfo | None = None


# ----------------------------------------------------------------------
class DynamicParameters:
    """A class that captures and organizes dynamic parameters."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        modules: list[Module],
    ) -> None:
        # ----------------------------------------------------------------------
        def ValidateName(name: str, *, allow_underscore: bool = False) -> str:
            if not name.isidentifier() or keyword.iskeyword(name):
                msg = f"'{name}' is not a valid identifier."
                raise ValueError(msg)

            if not allow_underscore and "_" in name:
                msg = f"'{name}' contains '_', which is not allowed."
                raise ValueError(msg)

            return name

        # ----------------------------------------------------------------------

        dynamic_parameters: dict[str, TyperParameter] = {}
        argument_lookup: dict[
            str,  # argument name
            tuple[
                str,  # module name
                str | None,  # requirement name
                str,  # parameter name
            ],
        ] = {}

        for module in modules:
            module_name = ValidateName(module.name)

            for parameter_name, parameter in module.GetParameters().items():
                full_parameter_name = f"{module_name}_{ValidateName(parameter_name, allow_underscore=True)}"

                if full_parameter_name in dynamic_parameters:
                    msg = f"The parameter name '{full_parameter_name}' is used by multiple modules."
                    raise ValueError(msg)

                dynamic_parameters[full_parameter_name] = parameter

                assert full_parameter_name not in argument_lookup, full_parameter_name
                argument_lookup[full_parameter_name] = (module.name, None, parameter_name)

            for query in module.queries:
                for requirement in query.requirements:
                    prefix = f"{module_name}_{ValidateName(requirement.name)}_"

                    for parameter_name, parameter in requirement.GetParameters().items():
                        full_parameter_name = f"{prefix}{ValidateName(parameter_name, allow_underscore=True)}"

                        if full_parameter_name in dynamic_parameters:
                            msg = f"The parameter name '{full_parameter_name}' is used by multiple requirements."
                            raise ValueError(msg)

                        dynamic_parameters[full_parameter_name] = parameter

                        assert full_parameter_name not in argument_lookup, full_parameter_name
                        argument_lookup[full_parameter_name] = (module.name, requirement.name, parameter_name)

        self.dynamic_parameters = dynamic_parameters
        self._argument_lookup = argument_lookup

    # ----------------------------------------------------------------------
    def Parse(
        self,
        kwargs: dict[str, object],
    ) -> dict[
        str,  # module name
        dict[
            str | None,  # requirement name
            dict[
                str,  # parameter name
                object,
            ],
        ],
    ]:
        """Parse command line arguments into a structured dictionary based on the dynamic parameters."""

        results: dict[str, dict[str | None, dict[str, object]]] = {}

        for arg_name, arg_value in kwargs.items():
            argument_info = self._argument_lookup.get(arg_name)
            if argument_info is None:
                msg = f"'{arg_name}' does not correspond to a valid parameter."
                raise ValueError(msg)

            module_name, requirement_name, parameter_name = argument_info

            results.setdefault(module_name, {}).setdefault(requirement_name, {})[parameter_name] = arg_value

        return results
