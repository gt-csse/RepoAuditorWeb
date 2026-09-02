import textwrap

from typing import TYPE_CHECKING

from dbrownell_Common import TextwrapEx

from RepoAuditorWeb.lib.execute import Execute
from RepoAuditorWeb.lib.requirement import EvaluateResultValue

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager

    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
def ExecuteExperience(  # noqa: C901, PLR0915
    dm: DoneManager,
    port: int,  # noqa: ARG001
    token: str,  # noqa: ARG001
    modules: list[Module],
    arguments: dict[str, dict[str | None, dict[str, object]]],
    *,
    display_resolution: bool = True,
    display_rationale: bool = True,
) -> None:
    """Execute the application in a console experience."""

    results = Execute(dm, modules, arguments)

    num_skipped = 0
    num_does_not_apply = 0
    num_success = 0
    num_warning = 0
    num_error = 0

    dm.WriteLine("\n")

    for result in results:
        if result.result == EvaluateResultValue.Skipped:
            num_skipped += 1
        elif result.result == EvaluateResultValue.DoesNotApply:
            num_does_not_apply += 1
        elif result.result == EvaluateResultValue.Success:
            num_success += 1
        elif result.result == EvaluateResultValue.Warning:
            num_warning += 1
        elif result.result == EvaluateResultValue.Error:
            num_error += 1
        else:
            assert False, result.result  # noqa: B011, PT015  # pragma: no cover

        if result.result in {EvaluateResultValue.Warning, EvaluateResultValue.Error} or dm.is_verbose:
            if result.result == EvaluateResultValue.Warning:
                write_func = dm.WriteWarning
            elif result.result == EvaluateResultValue.Error:
                write_func = dm.WriteError
            elif dm.is_verbose:
                write_func = dm.WriteVerbose
            else:
                assert False, result.result  # noqa: B011, PT015  # pragma: no cover

            header = f"Requirement '{result.requirement.name}'"
            write_func(header)
            write_func("=" * len(header))

            if result.context:
                write_func(TextwrapEx.Indent(result.context, 4))
                write_func(" \n")

            if display_resolution and result.resolution:
                header = "Resolution"
                write_func(TextwrapEx.Indent(header, 4))
                write_func(TextwrapEx.Indent("-" * len(header), 4))

                for line in result.resolution.splitlines():
                    write_func(TextwrapEx.Indent(line, 8))

                write_func(" \n")

            if display_rationale and result.rationale:
                header = "Rationale"
                write_func(TextwrapEx.Indent(header, 4))
                write_func(TextwrapEx.Indent("-" * len(header), 4))

                for line in result.rationale.splitlines():
                    write_func(TextwrapEx.Indent(line, 8))

                write_func(" \n")

            dm.WriteLine("\n")

    total = num_skipped + num_does_not_apply + num_success + num_warning + num_error

    # ----------------------------------------------------------------------
    def CalcPercentage(count: int) -> str:
        if total == 0:
            return "0.00%"

        return f"{(count / total) * 100:.2f}%"

    # ----------------------------------------------------------------------

    dm.WriteLine(
        textwrap.dedent(
            f"""\
            Skipped:            {num_skipped:>5} [{CalcPercentage(num_skipped)}]
            Does Not Apply:     {num_does_not_apply:>5} [{CalcPercentage(num_does_not_apply)}]
            Success:            {num_success:>5} [{CalcPercentage(num_success)}]
            Warning:            {num_warning:>5} [{CalcPercentage(num_warning)}]
            Error:              {num_error:>5} [{CalcPercentage(num_error)}]
            """,
        ),
    )
