import io

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from RepoAuditorWeb.lib.execute import Execute
from RepoAuditorWeb.lib.requirement import EvaluateResult, EvaluateResultValue

from conftest import EvaluateValues, MyModule, MyQuery, MyRequirement


# ----------------------------------------------------------------------
def _CreateRequirement(
    name: str = "MyRequirement",
    result: EvaluateResultValue = EvaluateResultValue.Success,
    context: str | None = None,
) -> MyRequirement:
    return MyRequirement(
        name,
        "My requirement description.",
        evaluate_values=EvaluateValues(result, context),
    )


# ----------------------------------------------------------------------
def _CreateModule(
    queries: list[MyQuery],
    name: str = "MyModule",
    *,
    requires_explicit_include: bool = False,
    raise_exception: Exception | None = None,
) -> MyModule:
    return MyModule(
        name,
        "My description.",
        queries,
        raise_exception=raise_exception,
        requires_explicit_include=requires_explicit_include,
    )


# ----------------------------------------------------------------------
def _Execute(modules, arguments) -> tuple[list[EvaluateResult], str, int]:
    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...", flags=DoneManagerFlags.Create()) as dm:
        results = Execute(dm, modules, arguments)
        result_code = dm.result

    return results, sink.getvalue(), result_code


# ----------------------------------------------------------------------
def test_NoModules():
    results, _, result_code = _Execute([], {})

    assert results == []
    assert result_code == 0


# ----------------------------------------------------------------------
def test_SingleRequirement():
    requirement = _CreateRequirement()
    module = _CreateModule([MyQuery("MyQuery", [requirement], query_data={"response": {}})])

    results, _, result_code = _Execute(
        [module], {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}}
    )

    assert [result.result for result in results] == [EvaluateResultValue.Success]
    assert results[0].requirement is requirement
    assert result_code == 0


# ----------------------------------------------------------------------
def test_MultipleRequirements():
    module = _CreateModule(
        [
            MyQuery(
                "MyQuery",
                [_CreateRequirement("One"), _CreateRequirement("Two")],
                query_data={"response": {}},
            ),
        ],
    )

    results, _, _ = _Execute(
        [module],
        {
            "MyModule": {
                None: {"skip": False},
                "One": {"skip": False},
                "Two": {"skip": False},
            },
        },
    )

    assert [result.requirement.name for result in results] == ["One", "Two"]


# ----------------------------------------------------------------------
def test_MultipleQueries():
    module = _CreateModule(
        [
            MyQuery("Query1", [_CreateRequirement("One")], query_data={"response": {}}),
            MyQuery("Query2", [_CreateRequirement("Two")], query_data={"response": {}}),
        ],
    )

    results, _, _ = _Execute(
        [module],
        {
            "MyModule": {
                None: {"skip": False},
                "One": {"skip": False},
                "Two": {"skip": False},
            },
        },
    )

    assert [result.requirement.name for result in results] == ["One", "Two"]


# ----------------------------------------------------------------------
def test_MultipleModules():
    modules = [
        _CreateModule([MyQuery("Query1", [_CreateRequirement("One")], query_data={})], "ModuleA"),
        _CreateModule([MyQuery("Query2", [_CreateRequirement("Two")], query_data={})], "ModuleB"),
    ]

    results, _, _ = _Execute(
        modules,
        {
            "ModuleA": {None: {"skip": False}, "One": {"skip": False}},
            "ModuleB": {None: {"skip": False}, "Two": {"skip": False}},
        },
    )

    assert [result.requirement.name for result in results] == ["One", "Two"]


# ----------------------------------------------------------------------
# Each result is attributed to the module that produced it so that its source can be displayed.
def test_ResultsAreAttributedToTheirModule():
    modules = [
        _CreateModule([MyQuery("Query1", [_CreateRequirement("One")], query_data={})], "ModuleA"),
        _CreateModule([MyQuery("Query2", [_CreateRequirement("Two")], query_data={})], "ModuleB"),
    ]

    results, _, _ = _Execute(
        modules,
        {
            "ModuleA": {None: {"skip": False}, "One": {"skip": False}},
            "ModuleB": {None: {"skip": False}, "Two": {"skip": False}},
        },
    )

    assert [result.module for result in results] == modules


# ----------------------------------------------------------------------
def test_ModuleNamesAppearInOutput():
    module = _CreateModule([MyQuery("MyQuery", [_CreateRequirement()], query_data={})])

    _, output, _ = _Execute([module], {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}})

    assert "Executing module 'MyModule' (1 of 1)..." in output
    assert "Executing query 'MyQuery' (1 of 1)..." in output
    assert "Evaluating requirement 'MyRequirement' (1 of 1)..." in output


# ----------------------------------------------------------------------
class TestSkip:
    # ----------------------------------------------------------------------
    def test_SkippedModuleProducesNoResults(self):
        query = MyQuery("MyQuery", [_CreateRequirement()], query_data={})
        module = _CreateModule([query])

        results, output, result_code = _Execute([module], {"MyModule": {None: {"skip": True}}})

        assert results == []
        assert "SKIPPED." in output
        assert result_code == 0

        # The query is never reached for a skipped module.
        assert query.module_data is None

    # ----------------------------------------------------------------------
    def test_ModuleRequiringExplicitIncludeIsSkippedByDefault(self):
        module = _CreateModule(
            [MyQuery("MyQuery", [_CreateRequirement()], query_data={})],
            requires_explicit_include=True,
        )

        results, _, _ = _Execute([module], {"MyModule": {None: {"include": False}}})

        assert results == []

    # ----------------------------------------------------------------------
    def test_SkippedQueryProducesNoResults(self):
        # A query returning None indicates that it has no data to evaluate against.
        module = _CreateModule([MyQuery("MyQuery", [_CreateRequirement()], query_data=None)])

        results, output, _ = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}},
        )

        assert results == []
        assert "SKIPPED." in output

    # ----------------------------------------------------------------------
    def test_SkippedRequirementIsReported(self):
        module = _CreateModule([MyQuery("MyQuery", [_CreateRequirement()], query_data={})])

        results, output, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": True}}},
        )

        assert [result.result for result in results] == [EvaluateResultValue.Skipped]
        assert [result.module for result in results] == [module]
        assert "SKIPPED" in output
        assert result_code == 0

    # ----------------------------------------------------------------------
    # Skipping one requirement must not prevent the others in the query from being evaluated.
    def test_OtherRequirementsAreStillEvaluated(self):
        module = _CreateModule(
            [
                MyQuery(
                    "MyQuery",
                    [_CreateRequirement("One"), _CreateRequirement("Two")],
                    query_data={},
                ),
            ],
        )

        results, _, _ = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "One": {"skip": True}, "Two": {"skip": False}}},
        )

        assert [(result.requirement.name, result.result) for result in results] == [
            ("One", EvaluateResultValue.Skipped),
            ("Two", EvaluateResultValue.Success),
        ]


# ----------------------------------------------------------------------
class TestResultCodes:
    # ----------------------------------------------------------------------
    def test_Warning(self):
        module = _CreateModule(
            [MyQuery("MyQuery", [_CreateRequirement(result=EvaluateResultValue.Warning)], query_data={})],
        )

        results, _, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}},
        )

        assert [result.result for result in results] == [EvaluateResultValue.Warning]
        assert result_code == 1

    # ----------------------------------------------------------------------
    def test_Error(self):
        module = _CreateModule(
            [MyQuery("MyQuery", [_CreateRequirement(result=EvaluateResultValue.Error)], query_data={})],
        )

        results, _, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}},
        )

        assert [result.result for result in results] == [EvaluateResultValue.Error]
        assert result_code == -1

    # ----------------------------------------------------------------------
    def test_WarningContextIsWritten(self):
        module = _CreateModule(
            [
                MyQuery(
                    "MyQuery",
                    [_CreateRequirement(result=EvaluateResultValue.Warning, context="My warning context.")],
                    query_data={},
                ),
            ],
        )

        _, output, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}},
        )

        assert "My warning context." in output
        assert result_code == 1

    # ----------------------------------------------------------------------
    def test_ErrorContextIsWritten(self):
        module = _CreateModule(
            [
                MyQuery(
                    "MyQuery",
                    [_CreateRequirement(result=EvaluateResultValue.Error, context="My error context.")],
                    query_data={},
                ),
            ],
        )

        _, output, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}},
        )

        assert "My error context." in output
        assert result_code == -1

    # ----------------------------------------------------------------------
    def test_DoesNotApply(self):
        module = _CreateModule(
            [
                MyQuery(
                    "MyQuery",
                    [_CreateRequirement(result=EvaluateResultValue.DoesNotApply)],
                    query_data={},
                ),
            ],
        )

        results, output, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}},
        )

        assert [result.result for result in results] == [EvaluateResultValue.DoesNotApply]
        assert "DOES NOT APPLY" in output
        assert result_code == 0

    # ----------------------------------------------------------------------
    # An error in one requirement must not prevent the others from being evaluated.
    def test_ErrorDoesNotPreventOtherRequirements(self):
        module = _CreateModule(
            [
                MyQuery(
                    "MyQuery",
                    [
                        _CreateRequirement("One", EvaluateResultValue.Error),
                        _CreateRequirement("Two", EvaluateResultValue.Success),
                    ],
                    query_data={},
                ),
            ],
        )

        results, _, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "One": {"skip": False}, "Two": {"skip": False}}},
        )

        assert [result.result for result in results] == [
            EvaluateResultValue.Error,
            EvaluateResultValue.Success,
        ]
        assert result_code == -1


# ----------------------------------------------------------------------
class TestDataFlow:
    # ----------------------------------------------------------------------
    def test_ModuleArgumentsAreForwarded(self):
        module = _CreateModule([MyQuery("MyQuery", [], query_data={})])
        arguments = {"MyModule": {None: {"skip": False}, "MyRequirement": {"skip": False}}}

        _Execute([module], arguments)

        assert module.module_data_args is arguments["MyModule"]

    # ----------------------------------------------------------------------
    # Queries receive the module-level data, which is filed under a None requirement name.
    def test_QueryReceivesModuleLevelData(self):
        query = MyQuery("MyQuery", [], query_data={})
        module = _CreateModule([query])
        module_arguments: dict = {None: {"skip": False, "value": 10}}

        _Execute([module], {"MyModule": module_arguments})

        assert query.module_data == {"skip": False, "value": 10}

    # ----------------------------------------------------------------------
    def test_RequirementReceivesQueryAndRequirementData(self):
        requirement = _CreateRequirement()
        query_data: dict[str, object] = {"response": {"description": "My description."}}
        module = _CreateModule([MyQuery("MyQuery", [requirement], query_data=query_data)])
        requirement_arguments: dict[str, object] = {"skip": False, "value": "populated"}

        _Execute([module], {"MyModule": {None: {"skip": False}, "MyRequirement": requirement_arguments}})

        assert requirement.evaluate_args is not None
        assert requirement.evaluate_args[0] is module
        assert requirement.evaluate_args[1] is query_data
        assert requirement.evaluate_args[2] is requirement_arguments

    # ----------------------------------------------------------------------
    # Modules with no corresponding arguments fall back to an empty dictionary, which the module
    # then rejects because the gating argument is absent.
    def test_MissingModuleArgumentsProduceNoResults(self):
        module = _CreateModule([MyQuery("MyQuery", [], query_data={})])

        results, _, result_code = _Execute([module], {})

        assert results == []
        assert result_code == -1


# ----------------------------------------------------------------------
class TestExceptions:
    # ----------------------------------------------------------------------
    # An exception raised while extracting module data is displayed and suppressed so that the
    # remaining modules are still executed.
    def test_ModuleExceptionIsSuppressed(self):
        modules = [
            _CreateModule(
                [MyQuery("Query1", [_CreateRequirement("One")], query_data={})],
                "ModuleA",
                raise_exception=ValueError("My module error."),
            ),
            _CreateModule([MyQuery("Query2", [_CreateRequirement("Two")], query_data={})], "ModuleB"),
        ]

        results, output, result_code = _Execute(
            modules,
            {
                "ModuleA": {None: {"skip": False}, "One": {"skip": False}},
                "ModuleB": {None: {"skip": False}, "Two": {"skip": False}},
            },
        )

        assert "My module error." in output
        assert [result.requirement.name for result in results] == ["Two"]
        assert result_code == -1

    # ----------------------------------------------------------------------
    # A module whose data could not be extracted has nothing for its queries to operate on, so the
    # queries are not executed.
    def test_ModuleExceptionSkipsQueries(self):
        query = MyQuery("MyQuery", [_CreateRequirement()], query_data={})
        module = _CreateModule([query], raise_exception=ValueError("My module error."))

        results, output, result_code = _Execute([module], {"MyModule": {None: {"skip": False}}})

        assert results == []
        assert "My module error." in output
        assert "Executing query 'MyQuery'" not in output
        assert query.module_data is None
        assert result_code == -1

    # ----------------------------------------------------------------------
    def test_QueryExceptionIsSuppressed(self):
        module = _CreateModule(
            [
                MyQuery(
                    "Query1",
                    [_CreateRequirement("One")],
                    raise_exception=ValueError("My query error."),
                ),
                MyQuery("Query2", [_CreateRequirement("Two")], query_data={}),
            ],
        )

        results, output, result_code = _Execute(
            [module],
            {"MyModule": {None: {"skip": False}, "One": {"skip": False}, "Two": {"skip": False}}},
        )

        assert "My query error." in output
        assert [result.requirement.name for result in results] == ["Two"]
        assert result_code == -1
