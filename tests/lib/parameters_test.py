import inspect

import pytest

from typer.models import OptionInfo

from RepoAuditorWeb.lib.parameters import TyperParameter


# ----------------------------------------------------------------------
def test_Defaults():
    param = TyperParameter(int)

    assert param.type is int
    assert param.default is inspect.Parameter.empty
    assert param.info is None


# ----------------------------------------------------------------------
def test_AllValues():
    info = OptionInfo(help="Help text")
    param = TyperParameter(str, "value", info)

    assert param.type is str
    assert param.default == "value"
    assert param.info is info


# ----------------------------------------------------------------------
def test_Frozen():
    param = TyperParameter(int, 10)

    with pytest.raises(AttributeError):
        param.default = 20  # ty: ignore[invalid-assignment]
