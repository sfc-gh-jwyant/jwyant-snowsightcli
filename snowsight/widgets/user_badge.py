from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class UserBadge(Widget):
    """Bottom-left widget showing user initials badge + display name."""

    def __init__(self, display_name: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._display_name = display_name

    def compose(self) -> ComposeResult:
        yield Static("", id="badge-content")

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        name = self._display_name or "—"
        parts = name.split()
        if len(parts) >= 2:
            initials = parts[0][0].upper() + parts[-1][0].upper()
        elif parts and parts[0]:
            initials = parts[0][:2].upper()
        else:
            initials = "??"

        text = Text(overflow="ellipsis", no_wrap=True)
        text.append(f" {initials} ", style="bold #0d1b2a on #29B5E8")
        text.append(f"  {name}", style="#e8f4fd")
        try:
            self.query_one("#badge-content", Static).update(text)
        except Exception:
            pass

    def update(self, display_name: str) -> None:
        self._display_name = display_name
        self._refresh()
