"""
core.py — Shared singleton state for the gitcat TUI session.
Passed through every screen constructor so all screens share the same context.
"""
from __future__ import annotations

from typing import Optional


class GitcatCore:
    """Shared singleton state for the TUI session.

    Attributes:
        github_token: Raw GitHub personal-access token (or OAuth token).
        user:         Dict returned by get_github_user (login, name, avatar_url …).
        current_repo: The repo dict currently selected by the user, or None.
        chat_sessions: Per-repo in-memory message lists keyed by repo_id (int).
                       Each entry is a list of {'role', 'content', 'created_at'} dicts.
    """

    def __init__(self, github_token: str, user: dict) -> None:
        self.github_token: str = github_token
        self.user: dict = user
        self.current_repo: Optional[dict] = None
        self.chat_sessions: dict[int, list] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def login(self) -> str:
        """GitHub username of the authenticated user."""
        return self.user.get("login", "?")

    def get_chat_messages(self, repo_id: int) -> list:
        """Return (and lazily create) the message list for *repo_id*."""
        if repo_id not in self.chat_sessions:
            self.chat_sessions[repo_id] = []
        return self.chat_sessions[repo_id]

    def clear_chat(self, repo_id: int) -> None:
        """Wipe conversation history for *repo_id*."""
        self.chat_sessions[repo_id] = []
