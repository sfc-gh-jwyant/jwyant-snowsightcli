from __future__ import annotations

import threading
import time
from typing import Any

import snowflake.connector

MAX_ROWS = 50_000


class SnowflakeClient:
    """Thread-safe Snowflake connection wrapper.

    All methods are blocking and intended to be called from worker threads
    via Textual's @work(thread=True) decorator.
    """

    def __init__(self, connection_params: dict[str, Any]) -> None:
        self._params = connection_params
        self._conn: snowflake.connector.SnowflakeConnection | None = None
        self._cursor_lock = threading.Lock()
        self._active_cursor: snowflake.connector.cursor.SnowflakeCursor | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._conn = snowflake.connector.connect(**self._params)

    def close(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ── Session metadata ──────────────────────────────────────────────────────

    def get_session_info(self) -> dict[str, str]:
        cur = self._conn.cursor()
        try:
            cur.execute(
                "SELECT CURRENT_USER(), CURRENT_ROLE(), "
                "CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()"
            )
            row = cur.fetchone() or ("", "", "", "", "")
            return {
                "user": row[0] or "",
                "role": row[1] or "",
                "warehouse": row[2] or "",
                "database": row[3] or "",
                "schema": row[4] or "",
            }
        finally:
            cur.close()

    # ── Object exploration ────────────────────────────────────────────────────

    def get_databases(self) -> list[str]:
        cur = self._conn.cursor()
        try:
            cur.execute("SHOW DATABASES")
            return [r[1] for r in cur.fetchall()]
        finally:
            cur.close()

    def get_schemas(self, database: str) -> list[str]:
        cur = self._conn.cursor()
        try:
            cur.execute(f'SHOW SCHEMAS IN DATABASE "{database}"')
            return [r[1] for r in cur.fetchall()]
        finally:
            cur.close()

    def get_objects(self, database: str, schema: str, obj_type: str) -> list[str]:
        """Return object names for the given SHOW keyword (e.g. 'TABLES')."""
        cur = self._conn.cursor()
        try:
            cur.execute(f'SHOW {obj_type} IN SCHEMA "{database}"."{schema}"')
            return [r[1] for r in cur.fetchall()]
        except Exception:
            return []
        finally:
            cur.close()

    # ── Query execution ───────────────────────────────────────────────────────

    def execute_query(
        self, sql: str
    ) -> tuple[list[str], list[tuple], float]:
        """Execute SQL and return (columns, rows, elapsed_seconds).

        Fetches at most MAX_ROWS rows. Intended to run in a worker thread.
        """
        cur = self._conn.cursor()
        with self._cursor_lock:
            self._active_cursor = cur
        try:
            start = time.monotonic()
            cur.execute(sql)
            rows = cur.fetchmany(MAX_ROWS) if cur.description else []
            elapsed = time.monotonic() - start
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return columns, list(rows), elapsed
        finally:
            with self._cursor_lock:
                self._active_cursor = None
            cur.close()

    def cancel_query(self) -> None:
        with self._cursor_lock:
            cur = self._active_cursor
        if cur:
            try:
                cur.cancel()
            except Exception:
                pass
