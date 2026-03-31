from __future__ import annotations

from pathlib import Path

from rich.align import Align
from rich.console import Group
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from snowsight.db.client import SnowflakeClient
from snowsight.widgets.editor_pane import EditorPane
from snowsight.widgets.explorer import ObjectExplorer
from snowsight.widgets.results_pane import ResultsPane
from snowsight.widgets.user_badge import UserBadge

_logo_ansi = Text.from_ansi(
    (Path(__file__).parent.parent / "snowflake_logo.ansi").read_text()
)
_LOGO = Group(
    Align.center(Text("Snowflake", style="bold #29B5E8")),
    Align.center(_logo_ansi),
    Align.center(Text("Snowsight CLI", style="#7ba8c4")),
)


class SnowSightApp(App):
    """Main TUI application."""

    CSS_PATH = "styles/app.tcss"

    BINDINGS = [
        ("ctrl+l", "focus_explorer", "Explorer"),
        ("ctrl+e", "focus_editor", "Editor"),
        ("ctrl+r", "focus_results", "Results"),
        ("escape", "cancel_query", "Cancel"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, client: SnowflakeClient, **kwargs) -> None:
        super().__init__(**kwargs)
        self._client = client
        self._query_running = False

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="left-panel"):
                yield Static(_LOGO, id="app-header")
                yield ObjectExplorer(self._client, id="explorer")
                yield UserBadge(id="user-badge")
            with Vertical(id="right-panel"):
                yield EditorPane(id="editor-pane")
                yield ResultsPane(id="results-pane")

    # ── Startup ───────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self._init_session()

    @work(thread=True)
    def _init_session(self) -> None:
        try:
            info = self._client.get_session_info()
        except Exception as exc:
            self.call_from_thread(
                self.query_one(ResultsPane).set_status,
                f"Connection error: {exc}",
            )
            return

        def _apply() -> None:
            self.query_one(EditorPane).update_context(info)
            self.query_one(UserBadge).update(info.get("user", ""))
            self.query_one(ResultsPane).set_status(
                f"Connected  |  User: {info.get('user', '')}  |  "
                f"Role: {info.get('role', '')}  |  "
                f"WH: {info.get('warehouse', '')}"
            )

        self.call_from_thread(_apply)

    # ── Query execution ───────────────────────────────────────────────────────

    def on_editor_pane_run_query(self, event: EditorPane.RunQuery) -> None:
        if self._query_running:
            return
        self._query_running = True
        self.query_one(ResultsPane).set_status("Running query…")
        self._execute_query(event.sql)

    @work(thread=True)
    def _execute_query(self, sql: str) -> None:
        try:
            columns, rows, elapsed = self._client.execute_query(sql)
            info = self._client.get_session_info()

            def _success() -> None:
                self.query_one(ResultsPane).load_results(columns, rows, elapsed)
                self.query_one(EditorPane).update_context(info)
                self._query_running = False

            self.call_from_thread(_success)

        except Exception as exc:
            def _error() -> None:
                self.query_one(ResultsPane).show_error(str(exc))
                self.query_one(ResultsPane).set_status(f"Error  |  {exc}")
                self._query_running = False

            self.call_from_thread(_error)

    # ── Tree messages ─────────────────────────────────────────────────────────

    def on_object_explorer_schema_selected(
        self, event: ObjectExplorer.SchemaSelected
    ) -> None:
        editor = self.query_one(EditorPane)
        editor.current_db = event.database
        editor.current_schema = event.schema

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_focus_explorer(self) -> None:
        self.query_one("#explorer").focus()

    def action_focus_editor(self) -> None:
        self.query_one("#sql-editor").focus()

    def action_focus_results(self) -> None:
        self.query_one("#results-table").focus()

    def action_cancel_query(self) -> None:
        if self._query_running:
            self._client.cancel_query()
            self.query_one(ResultsPane).set_status("Query cancelled")
            self._query_running = False
