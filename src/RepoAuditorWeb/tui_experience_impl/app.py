"""Contains the Textual application that backs the TUI experience."""

import functools

from typing import ClassVar, TYPE_CHECKING

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Collapsible, Footer, Header, Label, RichLog, Static

from RepoAuditorWeb.lib import form
from RepoAuditorWeb.lib.execute import Execute

# Textual resolves the annotations of a callback that is posted to the thread owning the widgets, so
# a type named in one is imported at runtime rather than only while type checking.
from RepoAuditorWeb.lib.requirement import EvaluateResult  # noqa: TC001
from RepoAuditorWeb.tui_experience_impl import fields, results
from RepoAuditorWeb.tui_experience_impl.log_sink import LogSink

if TYPE_CHECKING:
    from collections.abc import Iterator

    from textual.widget import Widget

    from RepoAuditorWeb.lib.dynamic_parameters import DynamicParameters
    from RepoAuditorWeb.lib.form import FormContainer, FormGroup
    from RepoAuditorWeb.lib.module import Module


# ----------------------------------------------------------------------
class AuditorApp(App):
    """Displays the arguments of every module, executes them, and displays the results."""

    TITLE = "RepoAuditor"

    CSS_PATH = "app.tcss"

    # Function keys are used because an Input binds most of the control keys for editing (notably
    # 'ctrl+d' to delete a character), which would shadow a binding declared here. 'f5' is avoided
    # because it conventionally refreshes rather than acts.
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("f2", "execute", "Execute"),
        ("f3", "reset", "Reset"),
        ("ctrl+q", "quit", "Quit"),
    ]

    # ----------------------------------------------------------------------
    def __init__(
        self,
        modules: list[Module],
        dynamic_parameters: DynamicParameters,
        arguments: dict[str, dict[str | None, dict[str, object]]],
        *,
        execute: bool = False,
        evaluate_all: bool = False,
        display_resolution: bool = True,
        display_rationale: bool = True,
        verbose: bool = False,
        debug: bool = False,
    ) -> None:
        super().__init__()

        self.modules = modules
        self.dynamic_parameters = dynamic_parameters
        self.arguments = arguments
        self.execute_on_start = execute
        self.evaluate_all = evaluate_all
        self.display_resolution = display_resolution
        self.display_rationale = display_rationale
        # 'debug' is a read-only property of the base class, so the flags are named as the
        # DoneManager that supplied them names them.
        self.is_verbose = verbose
        self.is_debug = debug

        self.groups = form.CreateGroups(dynamic_parameters, arguments)

        # The log is resolved once a run begins and retained so that the thread performing the run
        # does not query the widget tree that another thread owns. '_log' is a method of the base
        # class, so the attribute cannot be named for the widget alone.
        self._output_log: RichLog | None = None

        # Only one run may be in flight at a time; the control is disabled while a run is active so
        # that a second run cannot interleave its output into the log.
        self.is_executing = False

    # ----------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        """Create the sections that display the arguments, the output, and the results."""

        yield Header()

        with Vertical(id="body"):
            with VerticalScroll(id="arguments"):
                yield Label("Arguments", classes="heading")

                for group in self.groups:
                    yield from _EnumerateGroupWidgets(group)

            with Horizontal(id="actions"):
                yield Button("Execute", id="execute", variant="primary")
                yield Button("Reset", id="reset")
                yield Label("", id="status")

            with Vertical(id="output-section", classes="hidden"):
                yield Label("Output", classes="heading")

                # Output arrives as text written by DoneManager rather than as lines, so a log that
                # appends what it is given is what displays it.
                yield RichLog(id="output", wrap=True, markup=False)

            with VerticalScroll(id="results-section", classes="hidden"):
                yield Label("Results", classes="heading")
                yield Vertical(id="results")

        yield Footer()

    # ----------------------------------------------------------------------
    def on_mount(self) -> None:
        """Execute immediately when the caller asked for it."""

        if self.execute_on_start:
            self.ExecuteRequirements()

    # ----------------------------------------------------------------------
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Invoke the action of the button that was pressed."""

        if event.button.id == "execute":
            self.ExecuteRequirements()
        elif event.button.id == "reset":
            self.ResetResults()

    # ----------------------------------------------------------------------
    def action_execute(self) -> None:
        """Execute the requirements."""

        self.ExecuteRequirements()

    # ----------------------------------------------------------------------
    def action_reset(self) -> None:
        """Discard what the previous run produced."""

        self.ResetResults()

    # ----------------------------------------------------------------------
    def ResetResults(self) -> None:
        """Discard what the previous run produced, retaining what the user entered."""

        if self.is_executing:
            return

        self.query_one("#output", RichLog).clear()
        self.query_one("#output-section", Vertical).add_class("hidden")

        self.query_one("#results", Vertical).remove_children()
        self.query_one("#results-section", VerticalScroll).add_class("hidden")

        self.query_one("#status", Label).update("")

    # ----------------------------------------------------------------------
    def ExecuteRequirements(self) -> None:
        """Execute the requirements with the values the controls hold."""

        if self.is_executing:
            return

        self.is_executing = True

        self.query_one("#execute", Button).disabled = True
        self.query_one("#status", Label).update("Executing...")

        self._output_log = self.query_one("#output", RichLog)
        self._output_log.clear()
        self.query_one("#output-section", Vertical).remove_class("hidden")

        results_container = self.query_one("#results", Vertical)
        results_container.remove_children()
        self.query_one("#results-section", VerticalScroll).add_class("hidden")

        # The controls are read on the thread that owns them; the worker is given the values rather
        # than the widget tree.
        values = self.CreateValues()

        self.run_worker(
            functools.partial(self._Execute, values),
            thread=True,
            exclusive=True,
        )

    # ----------------------------------------------------------------------
    def CreateValues(self) -> dict[str, object]:
        """Collect what every control holds, keyed by the name its field is submitted under."""

        controls: dict[str, Widget] = {
            widget.id: widget for widget in self.query(".field-control") if widget.id is not None
        }

        values: dict[str, object] = {}

        for group in self.groups:
            for container in (group, *group.sections):
                values.update(fields.CreateValues(container.fields, controls))

        return values

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def _Execute(self, values: dict[str, object]) -> None:
        # The run happens on a worker thread, so everything that touches a widget is posted back to
        # the thread that owns it.
        assert self._output_log is not None

        sink = LogSink(self, self._output_log)

        try:
            # A value that cannot be coerced is reported in the output rather than raised out of the
            # application, so the conversion happens here. The result is retained so that the values
            # a run used are what the next one starts from.
            self.arguments.clear()
            self.arguments.update(form.ParseValues(self.dynamic_parameters, values))

            with DoneManager.Create(
                sink,
                "Executing...",
                flags=DoneManagerFlags.Create(verbose=self.is_verbose, debug=self.is_debug),
            ) as dm:
                evaluate_results = Execute(dm, self.modules, self.arguments, evaluate_all=self.evaluate_all)

            self.call_from_thread(self._DisplayResults, evaluate_results)
        except Exception as ex:
            self.call_from_thread(self._DisplayError, str(ex))
        finally:
            self.call_from_thread(self._CompleteExecution)

    # ----------------------------------------------------------------------
    def _DisplayResults(self, evaluate_results: list[EvaluateResult]) -> None:
        self.query_one("#results", Vertical).mount(
            *results.EnumerateResultWidgets(
                evaluate_results,
                display_resolution=self.display_resolution,
                display_rationale=self.display_rationale,
                verbose=self.is_verbose,
            ),
        )

        self.query_one("#results-section", VerticalScroll).remove_class("hidden")
        self.query_one("#status", Label).update("Execution completed.")

    # ----------------------------------------------------------------------
    def _DisplayError(self, message: str) -> None:
        self.query_one("#output", RichLog).write(message)
        self.query_one("#status", Label).update("Execution failed.")

    # ----------------------------------------------------------------------
    def _CompleteExecution(self) -> None:
        self.is_executing = False
        self.query_one("#execute", Button).disabled = False


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
def _EnumerateGroupWidgets(group: FormGroup) -> Iterator[Widget]:
    """Yield the widgets that display a module and its requirements."""

    children: list[Widget] = list(_EnumerateContainerWidgets(group))

    # Requirements of the same query are displayed together under its name, since what a requirement
    # is asking about is decided by the data its query collects.
    query_name = ""

    for section in group.sections:
        if section.query and section.query != query_name:
            query_name = section.query
            children.append(Static(query_name, classes="query"))

        children.append(
            Collapsible(
                *_EnumerateContainerWidgets(section),
                title=section.name,
                classes="section",
            ),
        )

    yield Collapsible(*children, title=group.name, classes="group")


# ----------------------------------------------------------------------
def _EnumerateContainerWidgets(container: FormContainer) -> Iterator[Widget]:
    """Yield the widgets that display a container's description and fields."""

    if container.description:
        yield Static(container.description, classes="description")

    for field in container.fields:
        yield fields.CreateField(field)
