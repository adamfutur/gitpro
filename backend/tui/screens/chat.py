"""
screens/chat.py — In-terminal AI chat for a repository.

Layout:
  ┌──────────────────────────────┐
  │  conversation history        │  (scrollable Static, grows upward)
  │                              │
  ├──────────────────────────────┤
  │  > Input box                 │
  └──────────────────────────────┘

Behaviour:
  - Conversation history persists across visits (stored in core.chat_sessions[repo_id]).
  - Each user message is processed in a @work(thread=True) worker using the same
    tool-calling pattern as routes/chat.py send_message().
  - User messages are shown in bold white; assistant replies in dim cyan.
  - ctrl+q → pop screen back to repo detail.
  - ctrl+l → clear conversation for this repo.
"""
from __future__ import annotations

import datetime
import os
import sys

_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Label, LoadingIndicator, Static

from tui.core import GitcatCore

_WELCOME = (
    "[dim]gitcat chat — ask anything about this repository.\n"
    "ctrl+l to clear  •  ctrl+q to exit[/dim]\n"
)


class ChatScreen(Screen):
    """Repository-scoped AI chat screen."""

    BINDINGS = [
        Binding("ctrl+q", "go_back", "Exit chat", show=True, priority=True),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
    ]

    CSS = """
    #history {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
    }
    LoadingIndicator {
        height: 1;
        display: none;
    }
    #thinking {
        height: 1;
        padding: 0 2;
        color: $text-muted;
        display: none;
    }
    #input-box {
        height: 3;
        margin: 0;
    }
    """

    def __init__(self, core: GitcatCore, repo: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self.core = core
        self.repo = repo
        self._busy: bool = False

    # ------------------------------------------------------------------
    # Composition
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(_WELCOME, id="history", markup=True, expand=True)
        yield LoadingIndicator(id="spinner")
        yield Static("[dim]Thinking…[/dim]", id="thinking", markup=True)
        yield Input(placeholder="  Ask something about this repo…", id="input-box")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        repo_name = self.repo.get("name", "repo")
        self.title = f"Chat — {repo_name}"
        self.sub_title = f"@{self.core.login}"
        # Render any existing conversation history.
        self._rebuild_history()
        self.query_one("#input-box", Input).focus()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "input-box":
            return
        message = event.value.strip()
        if not message or self._busy:
            return
        event.input.clear()
        self._send_message(message)

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------

    @work(thread=True)
    def _send_message(self, message: str) -> None:
        self.app.call_from_thread(self._set_busy, True, message)
        try:
            from services.gemini_service import call_gemini, call_gemini_with_tools
            from services.github_service import (
                get_repo_details,
                get_repo_readme,
                get_repo_files,
                get_file_content,
                get_repo_commits,
                get_repo_prs,
            )

            repo_id: int = self.repo["id"]
            messages = self.core.get_chat_messages(repo_id)

            # Build context string (same pattern as routes/chat.py).
            context = (
                "You are an expert AI coding assistant helping developers understand "
                "their GitHub repositories. You have tools to look up the README, list "
                "and read files, and view recent commits and pull requests. Only call a "
                "tool when the question actually requires that information."
            )

            owner = repo_name_str = None
            github_token = self.core.github_token
            try:
                details = get_repo_details(github_token, repo_id)
                owner = details["owner"]["login"]
                repo_name_str = details["name"]
                context += (
                    f"\n\n=== REPOSITORY ===\n"
                    f"Name: {details['name']}\n"
                    f"Description: {details.get('description', 'No description')}\n"
                    f"Language: {details['language']}\n"
                    f"Stars: {details['stargazers_count']}\n"
                    f"Forks: {details['forks_count']}\n"
                    f"Open Issues: {details['open_issues_count']}\n"
                )
            except Exception as e:
                print(f"[chat] context error: {e}")

            if messages:
                context += "\n=== CONVERSATION HISTORY ===\n"
                for msg in messages[-5:]:
                    context += f"{msg['role']}: {msg['content']}\n"

            tools = []
            if owner and repo_name_str:
                def get_readme() -> str:
                    """Get the repository's README file content."""
                    readme = get_repo_readme(github_token, owner, repo_name_str)
                    return readme[:4000] if readme else "No README found."

                def list_files(path: str = "") -> str:
                    """List files and folders in the repository at the given path. Use an empty path for the repository root."""
                    files = get_repo_files(github_token, owner, repo_name_str, path)
                    if not files:
                        return f"No files found at path '{path}'."
                    return "\n".join(f"{f['type']}: {f['path']}" for f in files)

                def read_file(path: str) -> str:
                    """Get the content of a specific file in the repository, given its path."""
                    content = get_file_content(github_token, owner, repo_name_str, path)
                    return content[:4000] if content else f"Could not read file: {path}"

                def get_recent_commits() -> str:
                    """Get the 5 most recent commits to the repository."""
                    commits = get_repo_commits(github_token, owner, repo_name_str)
                    if not commits:
                        return "No commits found."
                    return "\n".join(
                        f"- {c['commit']['message'].splitlines()[0]} "
                        f"(by {c['commit']['author']['name']}, {c['commit']['author']['date']})"
                        for c in commits
                    )

                def get_pull_requests() -> str:
                    """Get the 5 most recent pull requests for the repository."""
                    prs = get_repo_prs(github_token, owner, repo_name_str)
                    if not prs:
                        return "No pull requests found."
                    return "\n".join(
                        f"- PR #{pr['number']}: {pr['title']} "
                        f"(state: {pr['state']}, author: {pr['user']['login']})"
                        for pr in prs
                    )

                tools = [get_readme, list_files, read_file, get_recent_commits, get_pull_requests]

            if tools:
                ai_response = call_gemini_with_tools(message, tools, context)
            else:
                ai_response = call_gemini(message, context)

            now = datetime.datetime.utcnow().isoformat()
            messages.append({"role": "user", "content": message, "created_at": now})
            messages.append({"role": "assistant", "content": ai_response, "created_at": now})

            self.app.call_from_thread(self._on_response, ai_response)
        except Exception as exc:
            self.app.call_from_thread(self._on_response_error, str(exc))

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _set_busy(self, busy: bool, user_message: str = "") -> None:
        self._busy = busy
        spinner = self.query_one(LoadingIndicator)
        thinking = self.query_one("#thinking", Static)
        spinner.display = busy
        thinking.display = busy
        if busy and user_message:
            # Append user message to history immediately.
            self._append_to_history(f"[bold white]You:[/bold white] {user_message.replace('[', chr(92) + '[')}")

    def _on_response(self, ai_response: str) -> None:
        self._busy = False
        spinner = self.query_one(LoadingIndicator)
        thinking = self.query_one("#thinking", Static)
        spinner.display = False
        thinking.display = False
        safe = ai_response.replace("[", "\\[")
        self._append_to_history(f"[dim cyan]gitcat:[/dim cyan] {safe}")

    def _on_response_error(self, msg: str) -> None:
        self._busy = False
        self.query_one(LoadingIndicator).display = False
        self.query_one("#thinking", Static).display = False
        self._append_to_history(f"[red]Error: {msg.replace('[', chr(92) + '[')}[/red]")

    def _append_to_history(self, line: str) -> None:
        history = self.query_one("#history", Static)
        current = str(history.renderable)
        history.update(current + "\n" + line)

    def _rebuild_history(self) -> None:
        """Re-render full conversation from core.chat_sessions."""
        repo_id: int = self.repo["id"]
        messages = self.core.get_chat_messages(repo_id)
        if not messages:
            return
        history_widget = self.query_one("#history", Static)
        lines = [_WELCOME.rstrip()]
        for msg in messages:
            role = msg.get("role", "user")
            content = (msg.get("content") or "").replace("[", "\\[")
            if role == "user":
                lines.append(f"[bold white]You:[/bold white] {content}")
            else:
                lines.append(f"[dim cyan]gitcat:[/dim cyan] {content}")
        history_widget.update("\n".join(lines))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_clear_chat(self) -> None:
        repo_id: int = self.repo["id"]
        self.core.clear_chat(repo_id)
        self.query_one("#history", Static).update(_WELCOME)
        self.notify("Conversation cleared.")

    def action_go_back(self) -> None:
        self.app.pop_screen()
