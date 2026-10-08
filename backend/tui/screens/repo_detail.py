"""
screens/repo_detail.py — Repository overview and action menu.

Displays metadata for the selected repository, then presents a vertical
action menu the user navigates with arrow keys / Enter.

Actions:
  1. Analysis            → AnalysisScreen
  2. Pull Requests       → PullsScreen
  3. Auto-Fix            → AutoFixScreen
  4. Architecture Diagram → DiagramScreen
  5. Chat                → ChatScreen

Press q to go back to the repos screen.
"""
from __future__ import annotations

import os
import sys

_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from tui.core import GitcatCore


_ACTIONS = [
    ("analysis",   "🔍  Analysis"),
    ("pulls",      "🔀  Pull Requests"),
    ("autofix",    "🔧  Auto-Fix"),
    ("diagram",    "🗺   Architecture Diagram"),
    ("chat",       "💬  Chat"),
]


class RepoDetailScreen(Screen):
    """Overview and action launcher for a single repository."""

    BINDINGS = [
        Binding("q", "go_back", "Back", show=True),
    ]

    CSS = """
    #meta {
        padding: 1 2;
        color: $text;
    }
    #divider {
        height: 1;
        color: $text-muted;
        padding: 0 2;
    }
    #action-list {
        height: 1fr;
        padding: 0 2;
    }
    """

    def __init__(self, core: GitcatCore, repo: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.core = core
        self.repo = repo

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(self._build_meta(), id="meta", markup=True)
        yield Static("[dim]─────────────────────────────[/dim]", id="divider", markup=True)
        items = []
        for key, label in _ACTIONS:
            item = ListItem(Label(label))
            item.data = key  # type: ignore[attr-defined]
            items.append(item)
        yield ListView(*items, id="action-list")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        repo = self.repo
        self.title = repo.get("full_name", repo.get("name", "repo"))
        self.sub_title = f"@{self.core.login}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_meta(self) -> str:
        r = self.repo
        name = r.get("full_name") or r.get("name", "unknown")
        desc = r.get("description") or "[dim]No description[/dim]"
        lang = r.get("language") or "—"
        stars = r.get("stargazers_count") or r.get("stars_count") or 0
        forks = r.get("forks_count") or 0
        issues = r.get("open_issues_count") or 0
        branch = r.get("default_branch") or "main"
        priv = "🔒 Private" if r.get("private") else "🔓 Public"
        return (
            f"[bold]{name}[/bold]  {priv}\n"
            f"{desc}\n\n"
            f"[dim]Language:[/dim] [cyan]{lang}[/cyan]   "
            f"[dim]Stars:[/dim] [yellow]★{stars}[/yellow]   "
            f"[dim]Forks:[/dim] {forks}   "
            f"[dim]Open Issues:[/dim] {issues}   "
            f"[dim]Branch:[/dim] [green]{branch}[/green]"
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        action_key = getattr(event.item, "data", None)
        if action_key is None:
            return
        self._launch_action(action_key)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _launch_action(self, key: str) -> None:
        repo = self.repo
        core = self.core
        if key == "analysis":
            from tui.screens.analysis import AnalysisScreen
            self.app.push_screen(AnalysisScreen(core=core, repo=repo))
        elif key == "pulls":
            from tui.screens.pulls import PullsScreen
            self.app.push_screen(PullsScreen(core=core, repo=repo))
        elif key == "autofix":
            from tui.screens.autofix import AutoFixScreen
            self.app.push_screen(AutoFixScreen(core=core, repo=repo))
        elif key == "diagram":
            from tui.screens.diagram import DiagramScreen
            self.app.push_screen(DiagramScreen(core=core, repo=repo))
        elif key == "chat":
            from tui.screens.chat import ChatScreen
            self.app.push_screen(ChatScreen(core=core, repo=repo))

    def action_go_back(self) -> None:
        self.app.pop_screen()
