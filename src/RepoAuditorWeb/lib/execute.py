import copy

from typing import TYPE_CHECKING

from RepoAuditorWeb.lib.requirement import EvaluateResultValue

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.module import Module
    from RepoAuditorWeb.lib.requirement import EvaluateResult


# ----------------------------------------------------------------------
def Execute(
    dm: DoneManager,
    modules: list[Module],
    arguments: dict[
        str,  # Module name
        dict[
            str | None,  # Requirement name
            dict[
                str,  # parameter name
                object,
            ],
        ],
    ],
) -> list[EvaluateResult]:
    """Execute the modules with the given arguments."""

    eval_results: list[EvaluateResult] = []

    with dm.Nested("Executing...") as execute_dm:
        for module_index, module in enumerate(modules):
            with execute_dm.Nested(
                f"Executing module '{module.name}' ({module_index + 1} of {len(modules)})...",
                suffix="\n",
            ) as module_dm:
                with module_dm.Nested(
                    "Extracting data...",
                    suffix="\n",
                    suppress_exceptions=True,
                ) as extract_dm:
                    module_data = module.GetModuleData(arguments.get(module.name, {}))
                    if module_data is None:
                        extract_dm.WriteLine("SKIPPED.")
                        continue

                if extract_dm.result < 0:
                    continue

                for query_index, query in enumerate(module.queries):
                    with module_dm.Nested(
                        f"Executing query '{query.name}' ({query_index + 1} of {len(module.queries)})...",
                        suffix="\n",
                        suppress_exceptions=True,
                    ) as query_dm:
                        with query_dm.Nested(
                            "Extracting data...",
                            suffix="\n",
                        ) as extract_dm:
                            this_query_data = query.GetQueryData(copy.copy(module_data.get(None, {})))
                            if this_query_data is None:
                                extract_dm.WriteLine("SKIPPED.")
                                continue

                        for requirement_index, requirement in enumerate(query.requirements):
                            query_status: str | None = None

                            with query_dm.Nested(
                                f"Evaluating requirement '{requirement.name}' ({requirement_index + 1} of {len(query.requirements)})...",
                                lambda: query_status,  # noqa: B023
                                suppress_exceptions=True,
                            ) as requirement_dm:
                                requirement_data = module_data.get(requirement.name, {})

                                eval_result = requirement.Evaluate(
                                    module,
                                    this_query_data,
                                    requirement_data,
                                )
                                eval_results.append(eval_result)

                                if eval_result.result == EvaluateResultValue.Skipped:
                                    query_status = "SKIPPED"
                                elif eval_result.result == EvaluateResultValue.DoesNotApply:
                                    query_status = "DOES NOT APPLY"
                                elif eval_result.result == EvaluateResultValue.Success:
                                    pass
                                elif eval_result.result == EvaluateResultValue.Warning:
                                    requirement_dm.result = 1

                                    if isinstance(eval_result.context, str):
                                        requirement_dm.WriteWarning(eval_result.context)
                                elif eval_result.result == EvaluateResultValue.Error:
                                    requirement_dm.result = -1

                                    if isinstance(eval_result.context, str):
                                        requirement_dm.WriteError(eval_result.context)
                                else:
                                    assert False, eval_result.result  # noqa: B011, PT015  # pragma: no cover

    return eval_results
