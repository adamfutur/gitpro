"""
screens/diagram.py — Architecture diagram viewer.

Generates a Mermaid flowchart of the repository architecture using
generate_architecture_diagram (which calls Gemini internally).

On mount: starts background worker.
Shows a spinner + live stage messages while generating.
On completion: displays the raw Mermaid source in a scrollable read-only TextArea
with instructions to paste it into mermaid.live.

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
from textual.widgets import Footer, Header, Label, LoadingIndicator, Static, TextArea

from tui.core import GitcatCore


class DiagramScreen(Screen):
    """Architecture diagram generator and viewer."""

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
    #hint {
        height: 1;
        padding: 0 2;
        color: $text-muted;
    }
    #diagram-area {
        height: 1fr;
        margin: 0 1;
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
        yield Static("[dim]Generating architecture diagram…[/dim]", id="status", markup=True)
        yield LoadingIndicator(id="spinner")
        yield Static(
            "[dim]Paste the output into [bold]mermaid.live[/bold] to visualize[/dim]",
            id="hint",
            markup=True,
        )
        # Read-only TextArea for the diagram source.
        ta = TextArea(id="diagram-area", language="markdown")
        ta.read_only = True
        yield ta
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.title = f"Diagram — {self.repo.get('name', '')}"
        self.sub_title = f"@{self.core.login}"
        # Hide hint + textarea until we have content.
        self.query_one("#hint", Static).display = False
        self.query_one("#diagram-area", TextArea).display = False
        self._generate()

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    @work(thread=True)
    def _generate(self) -> None:
        try:
            from services.architecture import generate_architecture_diagram

            def on_stage(msg: str) -> None:
                self.app.call_from_thread(self._update_status, msg)

            result = generate_architecture_diagram(
                self.core.github_token, self.repo["id"], on_stage=on_stage
            )
            self.app.call_from_thread(self._on_done, result)
        except Exception as exc:
            self.app.call_from_thread(self._on_error, str(exc))

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _update_status(self, msg: str) -> None:
        self.query_one("#status", Static).update(f"[dim]{msg}[/dim]")

    def _on_done(self, result: dict) -> None:
        self.query_one(LoadingIndicator).display = False
        diagram: str = result.get("diagram") or ""
        repo_full = result.get("repo_full_name", self.repo.get("name", ""))

        if not diagram:
            self.query_one("#status", Static).update(
                "[yellow]⚠  Gemini returned an empty diagram. Try again later.[/yellow]"
            )
            return

        self.query_one("#status", Static).update(
            f"[green]✓  Diagram ready for [bold]{repo_full}[/bold][/green]"
        )
        self.query_one("#hint", Static).display = True
        ta = self.query_one("#diagram-area", TextArea)
        ta.display = True
        ta.load_text(f"```mermaid\n{diagram}\n```")

    def _on_error(self, msg: str) -> None:
        self.query_one(LoadingIndicator).display = False
        self.query_one("#status", Static).update(f"[red]Error: {msg}[/red]")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_go_back(self) -> None:
        self.app.pop_screen()
