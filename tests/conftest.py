"""Test doubles for the abstract Module, Query, and Requirement classes."""

from dataclasses import dataclass
from typing import override

from RepoAuditorWeb.lib.dynamic_parameters import TyperParameter
from RepoAuditorWeb.lib.module import Module
from RepoAuditorWeb.lib.query import Query
from RepoAuditorWeb.lib.requirement import (
    EvaluateResult,
    EvaluateResultValue,
    Markdown,
    Requirement,
)


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class EvaluateValues:
    """The values a MyRequirement produces, minus the module that is only known once evaluated."""

    result: EvaluateResultValue = EvaluateResultValue.Success
    context: Markdown | None = None
    resolution: Markdown | None = None
    rationale: Markdown | None = None


# ----------------------------------------------------------------------
class MyRequirement(Requirement):
    def __init__(
        self,
        *args,
        parameters: dict[str, TyperParameter] | None = None,
        evaluate_values: EvaluateValues | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.parameters = {} if parameters is None else parameters
        self.evaluate_values = evaluate_values

        # Captures the arguments of the most recent _EvaluateImpl invocation so tests can assert
        # what Evaluate forwarded to the derived class.
        self.evaluate_args: tuple[Module, dict[str, object], dict[str, object]] | None = None

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return self.parameters

    @override
    def _EvaluateImpl(
        self,
        module: Module,
        query_data: dict[str, object],
        requirement_data: dict[str, object],
    ) -> EvaluateResult:
        self.evaluate_args = (module, query_data, requirement_data)

        values = EvaluateValues() if self.evaluate_values is None else self.evaluate_values

        return EvaluateResult(
            values.result,
            values.context,
            values.resolution,
            values.rationale,
            self,
            module,
        )


# ----------------------------------------------------------------------
class MyQuery(Query):
    def __init__(
        self,
        *args,
        query_data: dict[str, object] | None = None,
        raise_exception: Exception | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.query_data = query_data
        self.raise_exception = raise_exception

        # Captures the module data most recently passed to GetQueryData.
        self.module_data: dict[str, object] | None = None

    @override
    def GetQueryData(self, module_data: dict[str, object]) -> dict[str, object] | None:
        if self.raise_exception is not None:
            raise self.raise_exception

        self.module_data = module_data
        return self.query_data


# ----------------------------------------------------------------------
class MyModule(Module):
    def __init__(
        self,
        *args,
        parameters: dict[str, TyperParameter] | None = None,
        module_data: dict[str | None, dict[str, object]] | None = None,
        raise_exception: Exception | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.parameters = {} if parameters is None else parameters
        self.module_data = module_data
        self.raise_exception = raise_exception

        # Captures the arguments most recently passed to _GetModuleDataImpl.
        self.module_data_args: dict[str | None, dict[str, object]] | None = None

    @override
    def _GetParametersImpl(self) -> dict[str, TyperParameter]:
        return self.parameters

    @override
    def _GetModuleDataImpl(
        self,
        arguments: dict[str | None, dict[str, object]],
    ) -> dict[str | None, dict[str, object]]:
        if self.raise_exception is not None:
            raise self.raise_exception

        self.module_data_args = arguments

        return arguments if self.module_data is None else self.module_data
