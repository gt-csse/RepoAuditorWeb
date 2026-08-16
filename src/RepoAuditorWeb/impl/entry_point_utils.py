import copy
import inspect
import re
import secrets
import socket
import sys

from typing import Annotated, get_args, get_origin, TYPE_CHECKING

import typer

from RepoAuditorWeb import __version__
from RepoAuditorWeb.lib.modules import MODULES
from RepoAuditorWeb.lib.parameters import TyperParameter

if TYPE_CHECKING:
    from collections.abc import Callable

    from typer.models import CommandFunctionType


# ----------------------------------------------------------------------
def GetUnusedPort() -> int:
    """Return an unused port number on the local machine."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ----------------------------------------------------------------------
def ResolvePort(port: int | None) -> int:
    """Resolve the port number to use for the server."""

    return port or GetUnusedPort()


# ----------------------------------------------------------------------
def ResolveToken(token: str | None) -> str:
    """Resolve the token to use for the server."""

    return token or secrets.token_urlsafe(32)


# ----------------------------------------------------------------------
def VersionCallback(value: bool) -> None:  # noqa: FBT001
    """Display the version number and exit."""

    if value:
        sys.stdout.write(f"{__version__}\n")
        raise typer.Exit()


# ----------------------------------------------------------------------
def dynamic_command(
    app: typer.Typer,
    dynamic_parameters: dict[str, TyperParameter],
    **app_command_kwargs,
) -> Callable[[CommandFunctionType], CommandFunctionType]:
    """Decorate a function to create a Typer command that supports dynamic parameters.

    Example:
        @dynamic_command(app, dynamic_parameters, help="My command help text")
        def my_command(fixed_param: str, **kwargs):
            # Command implementation here
            pass

    """

    dynamic_annotations = {name: _CreateAnnotation(name, param) for name, param in dynamic_parameters.items()}

    # ----------------------------------------------------------------------
    def Wrapper(original_func: CommandFunctionType) -> CommandFunctionType:

        signature = inspect.signature(original_func)

        original_params = {
            name: param
            for name, param in signature.parameters.items()
            if param.kind not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
        }

        fixed_names = tuple(original_params)
        fixed_parameters = {name: _CreateTyperParameter(param) for name, param in original_params.items()}
        fixed_annotations = {
            name: Annotated[param.type, param.info]  # ty: ignore[invalid-type-form]
            for name, param in fixed_parameters.items()
        }

        # ----------------------------------------------------------------------
        def Invoker(**all_kwargs) -> object:
            fixed = {name: all_kwargs.pop(name) for name in fixed_names}
            return original_func(**fixed, **all_kwargs)

        # ----------------------------------------------------------------------

        Invoker.__name__ = original_func.__name__  # ty: ignore[unresolved-attribute]
        Invoker.__doc__ = original_func.__doc__
        Invoker.__signature__ = inspect.Signature(  # ty: ignore[unresolved-attribute]
            parameters=[
                inspect.Parameter(
                    name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=fixed_parameters[name].default,
                    annotation=fixed_annotations[name],
                )
                for name in fixed_names
            ]
            + [
                inspect.Parameter(
                    name,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=dynamic_parameters[name].default,
                    annotation=annotation,
                )
                for name, annotation in dynamic_annotations.items()
            ],
        )
        Invoker.__annotations__ = {**fixed_annotations, **dynamic_annotations}

        return app.command(**app_command_kwargs)(Invoker)  # ty: ignore[invalid-return-type]

    # ----------------------------------------------------------------------

    return Wrapper


# ----------------------------------------------------------------------
def CreateTyperParameters() -> dict[str, TyperParameter]:
    """Create a dictionary of TyperParameters for all modules."""

    parameters: dict[str, TyperParameter] = {}

    for module in MODULES:
        for k, v in module.GetParameters().items():
            parameters[f"{module.name}_{k}"] = v

    return parameters


# ----------------------------------------------------------------------
def ResolveParameterValues(
    dynamic_parameters: dict[str, TyperParameter],
    kwargs: dict[str, object],
) -> dict[str, dict[str, object]]:
    """Resolve the module parameter values to serve to the web client.

    Command line arguments take precedence; anything not supplied falls back to the default the
    plugin declared.
    """

    results: dict[str | None, dict[str, object]] = {}

    # Process the command line arguments
    name_regex = re.compile(r"^(?P<module_name>[^_]+)_(?P<parameter_name>.+)$")
    module_names = {module.name for module in MODULES}

    for k, v in kwargs.items():
        match = name_regex.match(k)

        if match and match.group("module_name") in module_names:
            module_name = match.group("module_name")
            parameter_name = match.group("parameter_name")
        else:
            module_name = None
            parameter_name = k

        results.setdefault(module_name, {})[parameter_name] = v

    # Augment the results with the default values for any missing parameters
    for param_name, param in dynamic_parameters.items():
        match = name_regex.match(param_name)
        assert match is not None, param_name

        module_name = match.group("module_name")
        parameter_name = match.group("parameter_name")

        module_parameters = results.setdefault(module_name, {})

        if param.default is not inspect.Parameter.empty and parameter_name not in module_parameters:
            module_parameters[parameter_name] = param.default

    # Arguments without a module prefix are filed under None; they belong to the command line
    # itself rather than to a module, so they are not forwarded.
    return {module_name: parameters for module_name, parameters in results.items() if module_name is not None}


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _CreateTyperParameter(param: inspect.Parameter) -> TyperParameter:
    annotation = param.annotation

    if get_origin(annotation) is Annotated:
        args = get_args(annotation)
        param_type = args[0]
        info = next((a for a in args[1:] if isinstance(a, typer.models.ParameterInfo)), None)
        if info is not None:
            return TyperParameter(param_type, param.default, info)

    if annotation is not inspect.Parameter.empty:
        param_type = annotation
    elif param.default is not inspect.Parameter.empty and param.default is not None:
        param_type = type(param.default)
    else:
        param_type = str

    typer_help = f"Set {param.name}."

    if param.default is inspect.Parameter.empty:
        info = typer.Argument(help=typer_help)
    else:
        info = typer.Option(help=typer_help)

    return TyperParameter(param_type, param.default, info)


# ----------------------------------------------------------------------
def _CreateAnnotation(name: str, param: TyperParameter) -> object:
    # Copy the plugin-provided info so the option declaration ('--<name>') can be
    # populated without mutating the object owned by the plugin. For an Annotated-style
    # OptionInfo, typer reads the option name from the info's `default` attribute (see
    # typer.utils.get_params_from_function); a synthesized signature has no decorated
    # parameter name for typer to fall back on, so it must be supplied explicitly. The
    # plugins leave `default` as None (not the Ellipsis typer treats as "unset"), so
    # both are checked here.
    if param.info is None:
        msg = f"Parameter '{name}' does not define typer info."
        raise ValueError(msg)

    info = copy.copy(param.info)
    if info.default in (None, ...) and not info.param_decls:
        info.default = f"--{name.replace('_', '-')}"

    return Annotated[param.type, info]  # ty: ignore[invalid-type-form]
