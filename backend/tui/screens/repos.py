"""
screens/repos.py — Repository browser screen.

Lists all repositories for the authenticated user.
- Typing filters the list in real time (fuzzy match on name + language).
- Press Enter to open RepoDetailScreen for the selected repo.
- Press / to jump focus to the filter input.
- Press r to refresh the repo list.
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
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static
from textual import work
from rich.text import Text

from tui.core import GitcatCore


def _fuzzy_match(query: str, repo: dict) -> bool:
    """Return True if *query* appears anywhere in the name or language (case-insensitive)."""
    q = query.lower()
    return (
        q in (repo.get("name") or "").lower()
        or q in (repo.get("language") or "").lower()
        or q in (repo.get("full_name") or "").lower()
    )


def _repo_label(repo: dict) -> Text:
    """Build a Rich Text row for a single repo entry."""
    text = Text()
    text.append(repo.get("name", ""), style="bold white")
    lang = repo.get("language")
    if lang:
        text.append(f"  {lang}", style="dim")
    stars = repo.get("stargazers_count", 0) or repo.get("stars_count", 0)
    text.append(f"  ★{stars}", style="yellow")
    if repo.get("private"):
        text.append("  🔒", style="dim red")
    return text


class ReposScreen(Screen):
    """Repository browser — the home screen of gitcat."""

    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=True),
        Binding("/", "focus_filter", "Filter", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    CSS = """
    #status {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    #filter {
        height: 3;
        margin: 0 0 0 0;
    }
    #repo-list {
        height: 1fr;
    }
    """

    def __init__(self, core: GitcatCore, **kwargs) -> None:
        super().__init__(**kwargs)
        self.core = core
        self._all_repos: list[dict] = []

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(f"  [dim]@{self.core.login}[/dim]", id="status", markup=True)
        yield Input(placeholder="  / filter repos…", id="filter")
        yield ListView(id="repo-list")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.title = "gitcat"
        self.sub_title = f"@{self.core.login}"
        self._load_repos()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True)
    def _load_repos(self) -> None:
        self.app.call_from_thread(self._set_loading, True)
        try:
            from services.github_service import get_user_repos
            repos = get_user_repos(self.core.github_token)
            if not isinstance(repos, list):
                repos = []
            self.app.call_from_thread(self._on_repos_loaded, repos)
        except Exception as exc:
            self.app.call_from_thread(self._on_error, str(exc))

    # ------------------------------------------------------------------
    # UI update helpers (called from thread via call_from_thread)
    # ------------------------------------------------------------------

    def _set_loading(self, loading: bool) -> None:
        lv = self.query_one("#repo-list", ListView)
        lv.clear()
        if loading:
            lv.append(ListItem(Label("[dim]Loading repositories…[/dim]", markup=True)))

    def _on_repos_loaded(self, repos: list[dict]) -> None:
        self._all_repos = repos
        query = self.query_one("#filter", Input).value
        self._render_list(query)
        count = len(repos)
        self.query_one("#status", Static).update(
            f"  [dim]@{self.core.login}[/dim]  [green]{count} repos[/green]"
        )

    def _on_error(self, msg: str) -> None:
        lv = self.query_one("#repo-list", ListView)
        lv.clear()
        lv.append(ListItem(Label(f"[red]Error: {msg}[/red]", markup=True)))

    def _render_list(self, query: str = "") -> None:
        lv = self.query_one("#repo-list", ListView)
        lv.clear()
        repos = (
            [r for r in self._all_repos if _fuzzy_match(query, r)]
            if query.strip()
            else self._all_repos
        )
        if not repos:
            lv.append(ListItem(Label("[dim]No repos match.[/dim]", markup=True)))
            return
        for repo in repos:
            item = ListItem(Label(_repo_label(repo)))
            item.data = repo  # type: ignore[attr-defined]
            lv.append(item)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter":
            self._render_list(event.value)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        repo = getattr(event.item, "data", None)
        if repo is None:
            return
        self.core.current_repo = repo
        from tui.screens.repo_detail import RepoDetailScreen
        self.app.push_screen(RepoDetailScreen(core=self.core, repo=repo))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_refresh(self) -> None:
        self._load_repos()
        self.notify("Refreshing repositories…")

    def action_quit_app(self) -> None:
        self.app.exit()
