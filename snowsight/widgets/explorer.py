from __future__ import annotations

from dataclasses import dataclass

from textual import work
from textual.message import Message
from textual.widgets import Tree
from textual.widgets.tree import TreeNode


OBJECT_TYPES: list[tuple[str, str]] = [
    ("Tables", "TABLES"),
    ("Views", "VIEWS"),
    ("Dynamic Tables", "DYNAMIC TABLES"),
    ("Procedures", "PROCEDURES"),
    ("Functions", "FUNCTIONS"),
    ("Stages", "STAGES"),
    ("Streams", "STREAMS"),
    ("Tasks", "TASKS"),
    ("Sequences", "SEQUENCES"),
]


@dataclass
class NodeData:
    kind: str          # "database" | "schema" | "folder" | "object"
    name: str
    database: str = ""
    schema: str = ""
    object_type: str = ""
    loaded: bool = False


class ObjectExplorer(Tree):
    """Lazy-loading Snowflake object explorer tree.

    Databases are loaded on mount; schemas/folders/objects are fetched
    on first expand using background worker threads.
    """

    # ── Messages ──────────────────────────────────────────────────────────────

    class SchemaSelected(Message):
        def __init__(self, database: str, schema: str) -> None:
            super().__init__()
            self.database = database
            self.schema = schema

    class ObjectSelected(Message):
        def __init__(
            self, database: str, schema: str, obj_type: str, name: str
        ) -> None:
            super().__init__()
            self.database = database
            self.schema = schema
            self.obj_type = obj_type
            self.name = name

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def __init__(self, client, **kwargs) -> None:
        super().__init__("Databases", **kwargs)
        self._client = client
        self.show_root = False

    def on_mount(self) -> None:
        self._load_databases()

    # ── Workers ───────────────────────────────────────────────────────────────

    @work(thread=True)
    def _load_databases(self) -> None:
        try:
            databases = self._client.get_databases()
        except Exception as exc:
            self.app.call_from_thread(self._show_load_error, str(exc))
            return

        def _populate() -> None:
            self.clear()
            for db in databases:
                node = self.root.add(
                    db,
                    data=NodeData(kind="database", name=db, database=db),
                )
                node.allow_expand = True

        self.app.call_from_thread(_populate)

    @work(thread=True)
    def _load_schemas(self, node: TreeNode, database: str) -> None:
        try:
            schemas = self._client.get_schemas(database)
        except Exception:
            schemas = []

        def _populate() -> None:
            node.remove_children()
            for schema in schemas:
                child = node.add(
                    schema,
                    data=NodeData(
                        kind="schema",
                        name=schema,
                        database=database,
                        schema=schema,
                    ),
                )
                child.allow_expand = True
            if node.data:
                node.data.loaded = True

        self.app.call_from_thread(_populate)

    @work(thread=True)
    def _load_folders(self, node: TreeNode, database: str, schema: str) -> None:
        def _populate() -> None:
            node.remove_children()
            for label, obj_type in OBJECT_TYPES:
                folder = node.add(
                    label,
                    data=NodeData(
                        kind="folder",
                        name=label,
                        database=database,
                        schema=schema,
                        object_type=obj_type,
                    ),
                )
                folder.allow_expand = True
            if node.data:
                node.data.loaded = True

        self.app.call_from_thread(_populate)

    @work(thread=True)
    def _load_objects(
        self, node: TreeNode, database: str, schema: str, obj_type: str
    ) -> None:
        try:
            objects = self._client.get_objects(database, schema, obj_type)
        except Exception:
            objects = []

        def _populate() -> None:
            node.remove_children()
            for obj_name in objects:
                node.add_leaf(
                    obj_name,
                    data=NodeData(
                        kind="object",
                        name=obj_name,
                        database=database,
                        schema=schema,
                        object_type=obj_type,
                    ),
                )
            if node.data:
                node.data.loaded = True

        self.app.call_from_thread(_populate)

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        node = event.node
        data: NodeData | None = node.data
        if data is None or data.loaded:
            return

        if data.kind == "database":
            self._load_schemas(node, data.database)
        elif data.kind == "schema":
            self.post_message(self.SchemaSelected(data.database, data.schema))
            self._load_folders(node, data.database, data.schema)
        elif data.kind == "folder":
            self._load_objects(node, data.database, data.schema, data.object_type)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        data: NodeData | None = event.node.data
        if data and data.kind == "object":
            self.post_message(
                self.ObjectSelected(
                    data.database, data.schema, data.object_type, data.name
                )
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _show_load_error(self, msg: str) -> None:
        self.root.add_leaf(f"[red]Error: {msg}[/red]")
