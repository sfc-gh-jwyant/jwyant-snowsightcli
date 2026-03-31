from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, DataTable, RichLog, Static

PAGE_SIZE = 500


class ResultsPane(Widget):
    """Scrollable, paginated query results table.

    Key bindings:
        [  → previous page
        ]  → next page
    """

    BINDINGS = [
        ("[", "prev_page", "Prev page"),
        ("]", "next_page", "Next page"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._columns: list[str] = []
        self._rows: list[tuple] = []
        self._page = 0
        self._total_pages = 0

    # ── Composition ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield DataTable(id="results-table", show_header=True)
        yield RichLog(id="error-log", markup=True, highlight=True)
        yield Horizontal(
            Button("◀", id="prev-page"),
            Static("", id="page-label"),
            Button("▶", id="next-page"),
            id="pagination-bar",
        )
        yield Static("Ready", id="bottom-status-bar")

    def on_mount(self) -> None:
        self.query_one("#results-table", DataTable).cursor_type = "row"
        self._sync_pagination_bar()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_results(
        self, columns: list[str], rows: list[tuple], elapsed: float
    ) -> None:
        """Populate the table with query results and reset to page 1."""
        self._columns = columns
        self._rows = rows
        self._page = 0
        self._total_pages = (
            max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE) if rows else 0
        )

        # Hide error log
        self.query_one("#error-log", RichLog).remove_class("visible")

        self._render_page()

        row_count = len(rows)
        truncated = " (truncated at 50,000)" if row_count == 50_000 else ""
        self.query_one("#bottom-status-bar", Static).update(
            f"  {row_count:,} row{'s' if row_count != 1 else ''}{truncated}"
            f"  |  {elapsed:.3f}s"
        )
        self._sync_pagination_bar()

    def show_error(self, message: str) -> None:
        """Display an error message and clear the table."""
        log = self.query_one("#error-log", RichLog)
        log.add_class("visible")
        log.clear()
        log.write(f"[bold red]Error:[/bold red] {message}")

        self.query_one("#results-table", DataTable).clear(columns=True)
        self._columns = []
        self._rows = []
        self._total_pages = 0
        self._sync_pagination_bar()

    def set_status(self, text: str) -> None:
        try:
            self.query_one("#bottom-status-bar", Static).update(text)
        except Exception:
            pass

    # ── Pagination ────────────────────────────────────────────────────────────

    def _render_page(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.clear(columns=True)

        if not self._columns:
            return

        for col in self._columns:
            table.add_column(col, key=col)

        start = self._page * PAGE_SIZE
        page_rows = self._rows[start : start + PAGE_SIZE]
        for row in page_rows:
            table.add_row(*[str(v) if v is not None else "NULL" for v in row])

        label = self.query_one("#page-label", Static)
        if self._total_pages > 0:
            label.update(
                f"Page {self._page + 1} / {self._total_pages}"
                f"  ({len(self._rows):,} rows)"
            )
        else:
            label.update("No results")

    def action_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def action_next_page(self) -> None:
        if self._page < self._total_pages - 1:
            self._page += 1
            self._render_page()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "prev-page":
            self.action_prev_page()
        elif event.button.id == "next-page":
            self.action_next_page()

    def _sync_pagination_bar(self) -> None:
        bar = self.query_one("#pagination-bar", Horizontal)
        bar.display = self._total_pages > 1
