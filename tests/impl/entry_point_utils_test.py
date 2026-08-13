import inspect
import socket

from typing import Annotated, get_args

import pytest
import typer

from typer.models import ArgumentInfo, OptionInfo
from typer.testing import CliRunner

from RepoAuditorWeb import __version__
from RepoAuditorWeb.impl.entry_point_utils import (
    CreateTyperParameters,
    dynamic_command,
    GetUnusedPort,
    ResolveParameterValues,
    ResolvePort,
    ResolveToken,
    VersionCallback,
)
from RepoAuditorWeb.lib.typer_parameter import TyperParameter


# ----------------------------------------------------------------------
class TestGetUnusedPort:
    # ----------------------------------------------------------------------
    def test_InRange(self):
        port = GetUnusedPort()

        assert 1024 <= port <= 65535

    # ----------------------------------------------------------------------
    def test_IsBindable(self):
        port = GetUnusedPort()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))

    # ----------------------------------------------------------------------
    def test_ProbeSocketIsClosed(self):
        # The port is only usable by a caller if the probe socket released it.
        port = GetUnusedPort()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
            sock.listen(1)

            assert sock.getsockname()[1] == port

    # ----------------------------------------------------------------------
    def test_SkipsPortsInUse(self, monkeypatch):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)

            used_port = sock.getsockname()[1]
            unused_port = GetUnusedPort()

            # GetUnusedPort binds to port 0, so it will never return a port already in use.
            assert unused_port != used_port


# ----------------------------------------------------------------------
class TestResolvePort:
    # ----------------------------------------------------------------------
    def test_ExplicitValue(self):
        assert ResolvePort(1234) == 1234

    # ----------------------------------------------------------------------
    def test_None(self):
        assert 1024 <= ResolvePort(None) <= 65535


# ----------------------------------------------------------------------
class TestResolveToken:
    # ----------------------------------------------------------------------
    def test_ExplicitValue(self):
        assert ResolveToken("my_token") == "my_token"

    # ----------------------------------------------------------------------
    def test_None(self):
        token = ResolveToken(None)

        assert token
        assert ResolveToken(None) != token


# ----------------------------------------------------------------------
class TestVersionCallback:
    # ----------------------------------------------------------------------
    def test_False(self):
        assert VersionCallback(False) is None  # noqa: FBT003

    # ----------------------------------------------------------------------
    def test_True(self, capsys):
        with pytest.raises(typer.Exit):
            VersionCallback(True)  # noqa: FBT003

        assert capsys.readouterr().out == f"{__version__}\n"


# ----------------------------------------------------------------------
class TestCreateTyperParameters:
    # ----------------------------------------------------------------------
    def test_Names(self):
        assert set(CreateTyperParameters().keys()) == {
            "GitHub_three",
            "GitHub_four",
            "CommunityStandards_one",
            "CommunityStandards_two",
            "ScientificSoftware_five",
            "ScientificSoftware_six",
        }

    # ----------------------------------------------------------------------
    def test_Values(self):
        parameters = CreateTyperParameters()

        assert parameters["GitHub_three"].type is int
        assert parameters["GitHub_three"].default == 30
        assert parameters["ScientificSoftware_six"].type is bool
        assert parameters["ScientificSoftware_six"].default is False


# ----------------------------------------------------------------------
class TestResolveParameterValues:
    # Command line values are only recognized for modules registered in MODULES, so these tests
    # use real plugin names rather than synthetic ones.

    # ----------------------------------------------------------------------
    def test_CommandLineValues(self):
        assert ResolveParameterValues(
            {"GitHub_three": TyperParameter(int, 1, OptionInfo())},
            {"GitHub_three": 100},
        ) == {"GitHub": {"three": 100}}

    # ----------------------------------------------------------------------
    def test_Defaults(self):
        assert ResolveParameterValues(
            {"GitHub_three": TyperParameter(int, 1, OptionInfo())},
            {},
        ) == {"GitHub": {"three": 1}}

    # ----------------------------------------------------------------------
    def test_CommandLineTakesPrecedence(self):
        assert ResolveParameterValues(
            {
                "GitHub_three": TyperParameter(int, 1, OptionInfo()),
                "GitHub_four": TyperParameter(str, "2", OptionInfo()),
            },
            {"GitHub_three": 100},
        ) == {"GitHub": {"three": 100, "four": "2"}}

    # ----------------------------------------------------------------------
    def test_NoDefault(self):
        assert ResolveParameterValues(
            {"GitHub_three": TyperParameter(int, info=OptionInfo())},
            {},
        ) == {"GitHub": {}}

    # ----------------------------------------------------------------------
    def test_UnprefixedValuesAreNotForwarded(self):
        assert ResolveParameterValues({}, {"port": 1234, "verbose": True}) == {}

    # ----------------------------------------------------------------------
    def test_ParameterNamesWithUnderscores(self):
        assert ResolveParameterValues(
            {"GitHub_one_two_three": TyperParameter(int, 1, OptionInfo())},
            {"GitHub_one_two_three": 100},
        ) == {"GitHub": {"one_two_three": 100}}

    # ----------------------------------------------------------------------
    def test_MultipleModules(self):
        assert ResolveParameterValues(
            {
                "GitHub_three": TyperParameter(int, 1, OptionInfo()),
                "CommunityStandards_one": TyperParameter(str, "2", OptionInfo()),
            },
            {"CommunityStandards_one": "value"},
        ) == {"GitHub": {"three": 1}, "CommunityStandards": {"one": "value"}}

    # ----------------------------------------------------------------------
    def test_UnregisteredModuleValuesAreNotForwarded(self):
        # 'Module' is not a registered plugin, so the value is treated as a command line argument
        # rather than a module parameter. The declared default still populates the entry.
        assert ResolveParameterValues(
            {"Module_one": TyperParameter(int, 1, OptionInfo())},
            {"Module_one": 100},
        ) == {"Module": {"one": 1}}

    # ----------------------------------------------------------------------
    def test_UnderscoredValuesForUnknownModulesAreNotForwarded(self):
        assert ResolveParameterValues(
            {"GitHub_three": TyperParameter(int, 1, OptionInfo())},
            {"output_dir": "value"},
        ) == {"GitHub": {"three": 1}}

    # ----------------------------------------------------------------------
    def test_UnknownModuleDoesNotCreateAnEntry(self):
        assert ResolveParameterValues({}, {"output_dir": "value"}) == {}

    # ----------------------------------------------------------------------
    def test_UnknownModuleDoesNotShadowKnownModule(self):
        assert ResolveParameterValues(
            {"GitHub_three": TyperParameter(int, 1, OptionInfo())},
            {"GitHub_three": 100, "Other_two": "value"},
        ) == {"GitHub": {"three": 100}}

    # ----------------------------------------------------------------------
    def test_RegisteredModuleNameIsMatchedOnThePrefixOnly(self):
        # The module name is the segment before the first underscore, so an undeclared parameter
        # on a registered module is still forwarded.
        assert ResolveParameterValues(
            {"GitHub_three": TyperParameter(int, 1, OptionInfo())},
            {"GitHub_extra": "value"},
        ) == {"GitHub": {"extra": "value", "three": 1}}

    # ----------------------------------------------------------------------
    def test_AllRegisteredModulesAreRecognized(self):
        assert ResolveParameterValues(
            {},
            {
                "GitHub_three": 1,
                "CommunityStandards_one": 2,
                "ScientificSoftware_five": 3,
            },
        ) == {
            "GitHub": {"three": 1},
            "CommunityStandards": {"one": 2},
            "ScientificSoftware": {"five": 3},
        }

    # ----------------------------------------------------------------------
    def test_ErrorInvalidDynamicParameterName(self):
        with pytest.raises(AssertionError, match="noModulePrefix"):
            ResolveParameterValues({"noModulePrefix": TyperParameter(int, 1, OptionInfo())}, {})


# ----------------------------------------------------------------------
class TestDynamicCommand:
    # ----------------------------------------------------------------------
    @staticmethod
    def _CreateApp(dynamic_parameters, func):
        app = typer.Typer(pretty_exceptions_enable=False)
        dynamic_command(app, dynamic_parameters, no_args_is_help=False)(func)

        return app

    # ----------------------------------------------------------------------
    def test_DynamicDefaults(self):
        observed = {}

        def Func(**kwargs) -> None:
            observed.update(kwargs)

        app = self._CreateApp({"Module_one": TyperParameter(int, 1, OptionInfo(help="One"))}, Func)

        result = CliRunner().invoke(app, [])

        assert result.exit_code == 0, result.output
        assert observed == {"Module_one": 1}

    # ----------------------------------------------------------------------
    def test_DynamicValueOnCommandLine(self):
        observed = {}

        def Func(**kwargs) -> None:
            observed.update(kwargs)

        app = self._CreateApp({"Module_one": TyperParameter(int, 1, OptionInfo(help="One"))}, Func)

        result = CliRunner().invoke(app, ["--Module-one", "100"])

        assert result.exit_code == 0, result.output
        assert observed == {"Module_one": 100}

    # ----------------------------------------------------------------------
    def test_FixedAndDynamicParameters(self):
        observed = {}

        def Func(
            value: Annotated[str, typer.Option("--value", help="Value.")] = "default",
            **kwargs,
        ) -> None:
            observed["value"] = value
            observed.update(kwargs)

        app = self._CreateApp({"Module_one": TyperParameter(int, 1, OptionInfo(help="One"))}, Func)

        result = CliRunner().invoke(app, ["--value", "explicit", "--Module-one", "50"])

        assert result.exit_code == 0, result.output
        assert observed == {"value": "explicit", "Module_one": 50}

    # ----------------------------------------------------------------------
    def test_ParameterInfoProvidedByPluginIsNotMutated(self):
        info = OptionInfo(help="One")

        self._CreateApp({"Module_one": TyperParameter(int, 1, info)}, lambda **kwargs: None)

        assert info.default is None

    # ----------------------------------------------------------------------
    def test_ExistingParamDeclsAreNotOverridden(self):
        info = OptionInfo(param_decls=["--custom"], help="One")

        app = typer.Typer(pretty_exceptions_enable=False)
        invoker = dynamic_command(app, {"Module_one": TyperParameter(int, 1, info)})(lambda **kwargs: None)

        annotation_info = get_args(inspect.signature(invoker).parameters["Module_one"].annotation)[1]

        # The plugin's own declarations are preserved rather than replaced with '--Module-one'.
        assert annotation_info.param_decls == ["--custom"]

        # `default` is left as None, which typer cannot render into a click option.
        assert annotation_info.default is None

        with pytest.raises(AttributeError):
            CliRunner().invoke(app, ["--custom", "7"], catch_exceptions=False)

    # ----------------------------------------------------------------------
    def test_UnderscoresBecomeDashes(self):
        app = self._CreateApp(
            {"Module_one_two": TyperParameter(int, 1, OptionInfo(help="One"))},
            lambda **kwargs: None,
        )

        # Asserted against the registered names rather than help text, which rich reflows and
        # colors according to the ambient terminal.
        assert "--Module-one-two" in {
            decl for param in typer.main.get_command(app).params for decl in param.opts
        }

    # ----------------------------------------------------------------------
    def test_NameAndDocstringArePreserved(self):
        def MyCommand(**kwargs) -> None:
            """My command help text."""

        app = self._CreateApp({}, MyCommand)

        assert "My command help text." in CliRunner().invoke(app, ["--help"]).output

    # ----------------------------------------------------------------------
    def test_UnannotatedParameterWithDefault(self):
        observed = {}

        def Func(value="default", **kwargs) -> None:  # noqa: ANN001
            observed["value"] = value

        app = self._CreateApp({}, Func)

        result = CliRunner().invoke(app, ["--value", "explicit"])

        assert result.exit_code == 0, result.output
        assert observed == {"value": "explicit"}

    # ----------------------------------------------------------------------
    def test_UnannotatedParameterWithoutDefaultIsAnArgument(self):
        observed = {}

        def Func(value, **kwargs) -> None:  # noqa: ANN001
            observed["value"] = value

        app = self._CreateApp({}, Func)

        result = CliRunner().invoke(app, ["explicit"])

        assert result.exit_code == 0, result.output
        assert observed == {"value": "explicit"}

    # ----------------------------------------------------------------------
    def test_UnannotatedParameterDefaultingToNone(self):
        observed = {}

        def Func(value=None, **kwargs) -> None:  # noqa: ANN001
            observed["value"] = value

        app = self._CreateApp({}, Func)

        result = CliRunner().invoke(app, [])

        assert result.exit_code == 0, result.output
        assert observed == {"value": None}

    # ----------------------------------------------------------------------
    def test_AnnotatedWithoutParameterInfo(self):
        observed = {}

        def Func(value: Annotated[str, "not parameter info"] = "default", **kwargs) -> None:
            observed["value"] = value

        app = self._CreateApp({}, Func)

        result = CliRunner().invoke(app, ["--value", "explicit"])

        assert result.exit_code == 0, result.output
        assert observed == {"value": "explicit"}

    # ----------------------------------------------------------------------
    def test_SignatureIsSynthesized(self):
        def Func(value: Annotated[str, typer.Option("--value")] = "default", **kwargs) -> None:
            pass

        app = typer.Typer(pretty_exceptions_enable=False)
        invoker = dynamic_command(app, {"Module_one": TyperParameter(int, 1, OptionInfo())})(Func)

        parameters = inspect.signature(invoker).parameters

        assert list(parameters.keys()) == ["value", "Module_one"]
        assert all(param.kind == inspect.Parameter.KEYWORD_ONLY for param in parameters.values())
        assert parameters["value"].default == "default"
        assert parameters["Module_one"].default == 1

    # ----------------------------------------------------------------------
    def test_ErrorMissingParameterInfo(self):
        with pytest.raises(ValueError, match="Parameter 'Module_one' does not define typer info."):
            dynamic_command(typer.Typer(), {"Module_one": TyperParameter(int, 1)})
