import io
import re
import textwrap

from typing import ClassVar, TYPE_CHECKING

from dbrownell_Common import TextwrapEx
from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import ListElement, Markdown as RichMarkdown, MarkdownElement
from rich.segment import Segment

from RepoAuditorWeb.lib.execute import Execute
from RepoAuditorWeb.lib.requirement import EvaluateResultValue

if TYPE_CHECKING:
    from dbrownell_Common.Streams.DoneManager import DoneManager
    from markdown_it.token import Token

    from RepoAuditorWeb.lib.module import Module

    from RepoAuditorWeb.lib.requirement import Markdown


# ----------------------------------------------------------------------
def ExecuteExperience(  # noqa: C901
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
                for line in _RenderMarkdown(result.context):
                    write_func(TextwrapEx.Indent(line, 4) if line else line)

                write_func(" \n")

            for header, content in [
                ("Resolution", result.resolution if display_resolution else None),
                ("Rationale", result.rationale if display_rationale else None),
            ]:
                if not content:
                    continue

                write_func(TextwrapEx.Indent(header, 4))
                write_func(TextwrapEx.Indent("-" * len(header), 4))

                for line in _RenderMarkdown(content):
                    write_func(TextwrapEx.Indent(line, 8) if line else line)

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


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# The content is indented when written, so render into a narrower width to leave room for it.
_MARKDOWN_WIDTH = 100

# Code spans are matched first (and preserved as-is) so that '**' appearing within them is not
# mistaken for emphasis.
_STRONG_REGEX = re.compile(
    r"`[^`]*`|(?<!\*)\*\*(?P<content>[^\s*](?:[^*]*[^\s*])?)\*\*(?!\*)",
)


# ----------------------------------------------------------------------
class _OrderedListElement(ListElement):
    """List element that renders ordered items using the delimiter found in the source."""

    # ----------------------------------------------------------------------
    @classmethod
    def create(cls, markdown: RichMarkdown, token: Token) -> _OrderedListElement:  # noqa: ARG003
        instance = cls(token.type, int(token.attrs.get("start", 1)))

        # `markup` is the delimiter that followed the number in the source ('.' or ')').
        instance.delimiter = token.markup

        return instance

    # ----------------------------------------------------------------------
    def __init__(self, list_type: str, list_start: int | None) -> None:
        super().__init__(list_type, list_start)

        self.delimiter = "."

    # ----------------------------------------------------------------------
    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        number = 1 if self.list_start is None else self.list_start

        # rich's ListItem hardcodes the numeral format, so render each item against a width that
        # accounts for the prefix and prepend the prefix here.
        width = max(len(f"{number + index}{self.delimiter} ") for index in range(len(self.items)))
        render_options = options.update(width=options.max_width - width)

        for index, item in enumerate(self.items):
            prefix = f"{number + index}{self.delimiter}".ljust(width)

            for first, line in enumerate(
                console.render_lines(item.elements, render_options, style=item.style),
            ):
                yield Segment(prefix if first == 0 else " " * width)
                yield from line
                yield Segment("\n")


# ----------------------------------------------------------------------
class _Markdown(RichMarkdown):
    """Markdown renderer that preserves ordered list delimiters and quotes bold content."""

    elements: ClassVar[dict[str, type[MarkdownElement]]] = {
        **RichMarkdown.elements,
        "ordered_list_open": _OrderedListElement,
    }

    # ----------------------------------------------------------------------
    def __init__(self, markup: str, *, hyperlinks: bool = True) -> None:
        # Bold conveys meaning in the source (it names the control the user must interact with), but
        # that meaning is lost once color and styling are stripped for the console. Quoting is
        # applied to the source rather than the rendered segments because rich styles bullets and
        # headings as bold too, making the rendered style ambiguous.
        super().__init__(_QuoteStrongText(markup), hyperlinks=hyperlinks)


# ----------------------------------------------------------------------
def _QuoteStrongText(markup: str) -> str:
    """Surround the content of strong (bold) spans with quotes."""

    def Replace(match: re.Match) -> str:
        content = match.group("content")

        # A code span matched; preserve it verbatim.
        if content is None:
            return match.group(0)

        return f'"{content}"'

    return _STRONG_REGEX.sub(Replace, markup)


# ----------------------------------------------------------------------
def _RenderMarkdown(content: Markdown) -> list[str]:
    """Render Markdown content as plain text lines suitable for the console."""

    sink = io.StringIO()

    # Hyperlinks are disabled so that urls remain visible when the output is redirected to a file;
    # rich otherwise embeds them in terminal escape sequences and the url is lost.
    Console(file=sink, width=_MARKDOWN_WIDTH, no_color=True).print(
        _Markdown(content, hyperlinks=False),
    )

    # rich pads every line to the console width.
    lines = [line.rstrip() for line in sink.getvalue().splitlines()]

    while lines and not lines[-1]:
        lines.pop()

    return lines
