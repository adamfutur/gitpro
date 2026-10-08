"""
screens/autofix.py — Auto-fix scan, diff preview, and PR creation screen.

On mount:
  - Runs scan_for_fixes in a background thread.
  - If no fixes found, shows a message.
  - If fixes found, shows a selectable list with space to toggle selection.

Keybindings:
  a     → Apply selected fixes (shows y/n confirmation, then creates PR).
  space → Toggle current item's selection (handled via on_key).
  q     → Go back.
"""
from __future__ import annotations

import os
import sys

_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import (
    Footer,
    Header,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
)
from rich.text import Text

from tui.core import GitcatCore


def _fix_label(fix: dict, selected: bool) -> Text:
    text = Text()
    tick = "[x]" if selected else "[ ]"
    text.append(f"{tick} ", style="bold cyan" if selected else "dim")
    text.append(fix.get("file", "?"), style="bold white" if selected else "white")
    desc = fix.get("description", "")
    if desc:
        text.append(f"\n     {desc}", style="dim")
    return text


class AutoFixScreen(Screen):
    """Auto-fix scan, selection, and PR creation."""

    BINDINGS = [
        Binding("q", "go_back", "Back", show=True),
        Binding("a", "apply_fixes", "Apply", show=True),
        Binding("space", "toggle_selection", "Toggle", show=True),
    ]

    CSS = """
    #status {
        height: 1;
        padding: 0 2;
        color: $text-muted;
    }
    LoadingIndicator {
        height: 3;
    }
    #fix-list {
        height: 1fr;
    }
    #result-msg {
        height: 3;
        padding: 0 2;
    }
    """

    def __init__(self, core: GitcatCore, repo: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.core = core
        self.repo = repo
        self._fixes: list[dict] = []
        self._selected: set[int] = set()   # indices of selected fixes
        self._branch: str = "main"
        self._confirming: bool = False

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static("[dim]Scanning for safe fixes…[/dim]", id="status", markup=True)
        yield LoadingIndicator(id="spinner")
        yield ListView(id="fix-list")
        yield Static("", id="result-msg", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.title = f"Auto-Fix — {self.repo.get('name', '')}"
        self.sub_title = f"@{self.core.login}"
        self._scan()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True)
    def _scan(self) -> None:
        try:
            from services.auto_fix import scan_for_fixes

            def on_stage(msg: str) -> None:
                self.app.call_from_thread(self._update_status, msg)

            result = scan_for_fixes(
                self.core.github_token, self.repo["id"], on_stage=on_stage
            )
            self.app.call_from_thread(self._on_scan_done, result)
        except Exception as exc:
            self.app.call_from_thread(self._on_error, str(exc))

    @work(thread=True)
    def _apply(self) -> None:
        self.app.call_from_thread(self._update_status, "Creating PR on GitHub…")
        try:
            from services.auto_fix import create_fix_pr
            selected_fixes = [self._fixes[i] for i in sorted(self._selected)]
            pr = create_fix_pr(
                self.core.github_token,
                self.repo["id"],
                self._branch,
                selected_fixes,
            )
            url = pr.get("html_url", "PR created (URL unavailable)")
            self.app.call_from_thread(self._on_pr_created, url)
        except ValueError as exc:
            self.app.call_from_thread(self._on_error, str(exc))
        except Exception as exc:
            self.app.call_from_thread(self._on_error, str(exc))

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _update_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(f"[dim]{msg}[/dim]")

    def _on_scan_done(self, result: dict) -> None:
        self.query_one(LoadingIndicator).display = False
        self._fixes = result.get("fixes") or []
        self._branch = result.get("branch", "main")
        lv = self.query_one("#fix-list", ListView)
        lv.clear()

        if not self._fixes:
            self.query_one("#status", Static).update(
                "[green]✓  No safe fixes found — repository looks clean.[/green]"
            )
            return

        self.query_one("#status", Static).update(
            f"[dim]{len(self._fixes)} fix{'es' if len(self._fixes) != 1 else ''} found  "
            f"— Space to toggle, a to apply[/dim]"
        )
        # Pre-select all fixes.
        self._selected = set(range(len(self._fixes)))
        for idx, fix in enumerate(self._fixes):
            item = ListItem(Label(_fix_label(fix, selected=True)))
            item.data = idx  # type: ignore[attr-defined]
            lv.append(item)

    def _on_error(self, msg: str) -> None:
        self.query_one(LoadingIndicator).display = False
        self.query_one("#status", Static).update(f"[red]Error: {msg}[/red]")

    def _on_pr_created(self, url: str) -> None:
        self.query_one("#status", Static).update("[green]✓  PR created![/green]")
        self.query_one("#result-msg", Static).update(
            f"[bold green]Pull request opened:[/bold green]\n{url}"
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _refresh_item(self, lv: ListView, idx: int) -> None:
        """Re-render the label for item at *idx* to reflect selection state."""
        try:
            item = lv._nodes[idx]
            selected = idx in self._selected
            item.query_one(Label).update(_fix_label(self._fixes[idx], selected=selected))
        except Exception:
            pass  # index out of range during rapid interaction

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_selection(self) -> None:
        lv = self.query_one("#fix-list", ListView)
        highlighted = lv.index
        if highlighted is None or not self._fixes:
            return
        idx = int(highlighted)
        if idx in self._selected:
            self._selected.discard(idx)
        else:
            self._selected.add(idx)
        self._refresh_item(lv, idx)

    def action_apply_fixes(self) -> None:
        if not self._fixes:
            self.notify("Nothing to apply.")
            return
        if not self._selected:
            self.notify("No fixes selected — use Space to toggle.")
            return
        if self._confirming:
            return
        # Show inline confirmation prompt.
        self._confirming = True
        count = len(self._selected)
        self.query_one("#result-msg", Static).update(
            f"[yellow]This will create a PR on GitHub with {count} fix(es). "
            "Press [bold]y[/bold] to proceed or [bold]n[/bold] to cancel.[/yellow]"
        )

    def on_key(self, event) -> None:
        if self._confirming:
            if event.key == "y":
                self._confirming = False
                self.query_one("#result-msg", Static).update("")
                self.query_one(LoadingIndicator).display = True
                self._apply()
            elif event.key == "n":
                self._confirming = False
                self.query_one("#result-msg", Static).update("[dim]Cancelled.[/dim]")

    def action_go_back(self) -> None:
        self.app.pop_screen()
