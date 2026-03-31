from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static, TextArea


class EditorPane(Widget):
    """SQL editor widget with a top context status bar and run buttons.

    Key bindings:
        F5 / Ctrl+Enter  → Run Query (selection, or statement at cursor)
    """

    BINDINGS = [
        ("f5", "run_query", "Run Query"),
        ("ctrl+enter", "run_query", "Run Query"),
    ]

    current_db: reactive[str] = reactive("")
    current_schema: reactive[str] = reactive("")
    current_warehouse: reactive[str] = reactive("")
    current_role: reactive[str] = reactive("")

    # ── Messages ──────────────────────────────────────────────────────────────

    class RunQuery(Message):
        def __init__(self, sql: str) -> None:
            super().__init__()
            self.sql = sql

    # ── Composition ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static("Not connected", id="editor-status-bar")
        with Horizontal(id="editor-toolbar"):
            yield Button("Run Query", id="run-query-btn")
            yield Button("Run All ▶", id="run-all-btn")
        yield TextArea.code_editor("", language="sql", theme="monokai", id="sql-editor")

    # ── Reactive watchers ─────────────────────────────────────────────────────

    def watch_current_db(self, _: str) -> None:
        self._refresh_status()

    def watch_current_schema(self, _: str) -> None:
        self._refresh_status()

    def watch_current_warehouse(self, _: str) -> None:
        self._refresh_status()

    def watch_current_role(self, _: str) -> None:
        self._refresh_status()

    def _refresh_status(self) -> None:
        parts: list[str] = []
        if self.current_db:
            parts.append(f"DB: {self.current_db}")
        if self.current_schema:
            parts.append(f"Schema: {self.current_schema}")
        if self.current_warehouse:
            parts.append(f"WH: {self.current_warehouse}")
        if self.current_role:
            parts.append(f"Role: {self.current_role}")
        text = "  |  ".join(parts) if parts else "Not connected"
        try:
            self.query_one("#editor-status-bar", Static).update(text)
        except Exception:
            pass

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_run_query(self) -> None:
        """Run selected text, or the statement under the cursor."""
        editor = self.query_one("#sql-editor", TextArea)
        sql = editor.selected_text.strip()
        if not sql:
            sql = self._statement_at_cursor()
        if sql:
            self.post_message(self.RunQuery(sql))

    def action_run_all(self) -> None:
        """Run the entire editor contents as one batch."""
        editor = self.query_one("#sql-editor", TextArea)
        sql = editor.text.strip()
        if sql:
            self.post_message(self.RunQuery(sql))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "run-query-btn":
            self.action_run_query()
        elif event.button.id == "run-all-btn":
            self.action_run_all()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _statement_at_cursor(self) -> str:
        """Return the SQL statement the cursor is currently inside.

        Statements are delimited by semicolons.  Falls back to the full
        editor text when no semicolons are present.
        """
        editor = self.query_one("#sql-editor", TextArea)
        text = editor.text
        if not text.strip():
            return ""

        cursor_row, cursor_col = editor.cursor_location
        lines = text.split("\n")
        # Absolute character offset of the cursor position
        offset = sum(len(lines[i]) + 1 for i in range(cursor_row)) + cursor_col

        pos = 0
        for segment in text.split(";"):
            end = pos + len(segment)
            if pos <= offset <= end:
                cleaned = segment.strip()
                return cleaned if cleaned else text.strip()
            pos = end + 1  # +1 for the semicolon

        return text.strip()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_context(self, info: dict[str, str]) -> None:
        """Update all reactive context fields at once."""
        self.current_db = info.get("database", "")
        self.current_schema = info.get("schema", "")
        self.current_warehouse = info.get("warehouse", "")
        self.current_role = info.get("role", "")
