import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.typer_parameter import TyperParameter


# ----------------------------------------------------------------------
class MyModule(Module):
    def GetParameters(self) -> dict[str, TyperParameter]:
        return {"value": TyperParameter(int, 10, OptionInfo(help="Value"))}


# ----------------------------------------------------------------------
def test_Construct():
    module = MyModule("MyName", "My description.")

    assert module.name == "MyName"
    assert module.description == "My description."
    assert module.requires_explicit_include is False


# ----------------------------------------------------------------------
def test_RequiresExplicitInclude():
    module = MyModule("MyName", "My description.", requires_explicit_include=True)

    assert module.requires_explicit_include is True


# ----------------------------------------------------------------------
def test_GetParameters():
    parameters = MyModule("MyName", "My description.").GetParameters()

    assert list(parameters.keys()) == ["value"]
    assert parameters["value"].type is int
    assert parameters["value"].default == 10


# ----------------------------------------------------------------------
def test_ErrorUnderscoreInName():
    with pytest.raises(AssertionError, match="Module names cannot contain underscores"):
        MyModule("My_Name", "My description.")


# ----------------------------------------------------------------------
def test_ErrorAbstract():
    with pytest.raises(TypeError):
        Module("MyName", "My description.")
