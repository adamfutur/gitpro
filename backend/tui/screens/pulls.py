"""
screens/pulls.py — Pull Request list and AI review screen.

On mount:
  - Loads open PRs in a background thread.
  - Displays them as a selectable list.

Selecting a PR:
  - Runs build_pr_review in a background thread (shows spinner while waiting).
  - Pushes ReviewScreen with the completed review.

Press q to go back.
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
from textual.widgets import Footer, Header, Label, ListItem, ListView, LoadingIndicator, Static
from rich.text import Text

from tui.core import GitcatCore


def _pr_label(pr: dict) -> Text:
    text = Text()
    num = pr.get("number", "?")
    title = pr.get("title", "Untitled")
    author = (pr.get("user") or {}).get("login", "?")
    created = (pr.get("created_at") or "")[:10]
    text.append(f"#{num} ", style="bold cyan")
    text.append(title, style="white")
    text.append(f"  ({author})", style="dim")
    text.append(f"  {created}", style="dim yellow")
    return text


class PullsScreen(Screen):
    """Open PR list for a repository."""

    BINDINGS = [
        Binding("q", "go_back", "Back", show=True),
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
    #pr-list {
        height: 1fr;
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
        yield Static("[dim]Loading pull requests…[/dim]", id="status", markup=True)
        yield LoadingIndicator(id="spinner")
        yield ListView(id="pr-list")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.title = f"PRs — {self.repo.get('name', '')}"
        self.sub_title = f"@{self.core.login}"
        self._load_prs()

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True)
    def _load_prs(self) -> None:
        try:
            from services.github_service import get_repo_details, list_pull_requests
            details = get_repo_details(self.core.github_token, self.repo["id"])
            owner = details["owner"]["login"]
            repo_name = details["name"]
            prs = list_pull_requests(
                self.core.github_token, owner, repo_name, state="open", per_page=30
            )
            self.app.call_from_thread(self._on_prs_loaded, prs)
        except Exception as exc:
            self.app.call_from_thread(self._on_error, str(exc))

    @work(thread=True)
    def _review_pr(self, pr: dict) -> None:
        self.app.call_from_thread(self._set_reviewing, True)
        try:
            from services.pr_review import build_pr_review
            stages: list[str] = []

            def on_stage(msg: str) -> None:
                stages.append(msg)
                self.app.call_from_thread(self._update_status, msg)

            result, owner, repo_name = build_pr_review(
                self.core.github_token,
                self.repo["id"],
                pr["number"],
                on_stage=on_stage,
            )
            self.app.call_from_thread(self._on_review_done, result)
        except Exception as exc:
            self.app.call_from_thread(self._on_review_error, str(exc))

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _on_prs_loaded(self, prs: list[dict]) -> None:
        self.query_one(LoadingIndicator).display = False
        lv = self.query_one("#pr-list", ListView)
        lv.clear()
        if not prs:
            self.query_one("#status", Static).update("[dim]No open pull requests.[/dim]")
            return
        self.query_one("#status", Static).update(
            f"[dim]{len(prs)} open PR{'s' if len(prs) != 1 else ''} — Enter to review[/dim]"
        )
        for pr in prs:
            item = ListItem(Label(_pr_label(pr)))
            item.data = pr  # type: ignore[attr-defined]
            lv.append(item)

    def _on_error(self, msg: str) -> None:
        self.query_one(LoadingIndicator).display = False
        self.query_one("#status", Static).update(f"[red]Error: {msg}[/red]")

    def _set_reviewing(self, reviewing: bool) -> None:
        self.query_one(LoadingIndicator).display = reviewing
        if reviewing:
            self.query_one("#status", Static).update("[dim]Building review…[/dim]")

    def _update_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(f"[dim]{msg}[/dim]")

    def _on_review_done(self, result: dict) -> None:
        self.query_one(LoadingIndicator).display = False
        self.query_one("#status", Static).update(
            f"[dim]{len(self.query_one('#pr-list', ListView)._nodes)} open PRs[/dim]"
        )
        self.app.push_screen(ReviewScreen(core=self.core, review=result))

    def _on_review_error(self, msg: str) -> None:
        self.query_one(LoadingIndicator).display = False
        self.query_one("#status", Static).update(f"[red]Review failed: {msg}[/red]")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        pr = getattr(event.item, "data", None)
        if pr is None:
            return
        self._review_pr(pr)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ---------------------------------------------------------------------------
# Review sub-screen (pushed on top of PullsScreen)
# ---------------------------------------------------------------------------

class ReviewScreen(Screen):
    """Displays the full AI review for a single PR."""

    BINDINGS = [
        Binding("q", "go_back", "Back", show=True),
    ]

    CSS = """
    #review-body {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    """

    def __init__(self, core: GitcatCore, review: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.core = core
        self.review = review

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(self._build_content(), id="review-body", markup=True, expand=True)
        yield Footer()

    def on_mount(self) -> None:
        pr_num = self.review.get("pr_number", "")
        title = self.review.get("title", "")
        self.title = f"PR #{pr_num} — {title}"
        self.sub_title = f"@{self.core.login}"

    def _build_content(self) -> str:
        r = self.review
        verdict = r.get("verdict") or {}
        status = verdict.get("status", "pass")
        reason = verdict.get("reason", "")
        v_colour = "green" if status == "pass" else "red"
        v_icon = "✓ PASS" if status == "pass" else "✗ FAIL"

        lines: list[str] = [
            f"[bold]PR #{r.get('pr_number')}[/bold]  {r.get('title', '')}",
            f"[dim]Author:[/dim] {r.get('author', '?')}  "
            f"[dim]Files:[/dim] {r.get('files_changed', 0)}  "
            f"[dim]+{r.get('additions', 0)} / -{r.get('deletions', 0)}[/dim]",
            "",
            f"[{v_colour}][bold]{v_icon}[/bold][/{v_colour}]  {reason}",
            "",
            "[dim]─────────────────────────────────────[/dim]",
            "",
        ]
        safe_review = (r.get("review") or "").replace("[", "\\[")
        lines.append(safe_review)
        return "\n".join(lines)

    def action_go_back(self) -> None:
        self.app.pop_screen()
