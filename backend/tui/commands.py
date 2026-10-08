"""
commands.py — Command palette provider for the gitcat TUI.

Exposes every user-facing action as a searchable command so the user can
open the palette (ctrl+p) and pick from the full list instead of hunting
for keybindings:

  Repos           Refresh repos
  Repo detail     Analysis, Pull Requests, Auto-Fix, Architecture Diagram, Chat, Back
  Chat            Clear chat
  Global          Quit

Commands are context-aware: only actions that make sense on the current
screen are offered, and the list re-renders whenever the screen changes.
"""
from __future__ import annotations

import os
import sys
from typing import AsyncGenerator

_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from textual.command import DiscoveryHit, Hit, Provider  # noqa: E402


class GitcatCommandProvider(Provider):
    """Dynamic command provider — builds hits from the current screen state."""

    async def startup(self) -> None:
        # Cache the core reference so search/discover don't re-walk the screen tree.
        self._core = getattr(self.screen, "core", None)

    # ------------------------------------------------------------------
    # Discovery (shown when the palette opens with an empty query)
    # ------------------------------------------------------------------

    async def discover(self) -> AsyncGenerator:
        for name, callback, help_text, _discoverable in self._commands():
            yield DiscoveryHit(name, callback, help=help_text, text=name)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: str) -> AsyncGenerator:
        matcher = self.matcher(query)

        for name, callback, help_text, discoverable in self._commands():
            if discoverable:
                continue  # discovery hits are surfaced via discover()
            match = matcher.match(name)
            if match > 0:
                yield Hit(
                    match,
                    matcher.highlight(name),
                    callback,
                    help=help_text,
                    text=name,
                )

    # ------------------------------------------------------------------
    # Command table
    # ------------------------------------------------------------------

    def _commands(self) -> list[tuple[str, callable, str, bool]]:
        """Return (name, callback, help, discoverable) tuples for the current screen.

        Callbacks are bound via closures so each command carries its own
        payload — Textual invokes `command()` with no arguments.
        """
        screen = self.screen
        commands: list[tuple[str, callable, str, bool]] = []

        # Global actions — available on every screen.
        commands.append(("Quit", self._quit, "Exit gitcat", True))

        # Repos screen.
        from tui.screens.repos import ReposScreen
        if isinstance(screen, ReposScreen):
            commands.append(
                ("Refresh repos", self._refresh_repos, "Re-fetch repository list from GitHub", True)
            )
            return commands

        # Repo detail screen — the action launcher.
        from tui.screens.repo_detail import RepoDetailScreen
        if isinstance(screen, RepoDetailScreen):
            for key, label in _REPO_ACTIONS:
                commands.append(
                    (label, self._make_push(key), f"Open {label.lower()} for this repo", True)
                )
            commands.append(("Back", self._pop, "Return to repository list", True))
            return commands

        # Feature screens — all share the same "back to repo detail" action.
        feature_screens = (
            "AnalysisScreen",
            "PullsScreen",
            "AutoFixScreen",
            "DiagramScreen",
            "ChatScreen",
        )
        if type(screen).__name__ in feature_screens:
            commands.append(("Back", self._pop, "Return to repository overview", True))
            if type(screen).__name__ == "ChatScreen":
                commands.append(
                    ("Clear chat", self._clear_chat, "Wipe conversation for this repo", True)
                )
            return commands

        return commands

    # ------------------------------------------------------------------
    # Callback adapters
    # ------------------------------------------------------------------

    def _quit(self) -> None:
        self.app.exit()

    def _refresh_repos(self) -> None:
        from tui.screens.repos import ReposScreen
        screen = self.screen
        if isinstance(screen, ReposScreen):
            screen.action_refresh()

    def _make_push(self, action_key: str):
        """Return a closure that pushes the named feature screen."""
        from tui.screens.repo_detail import RepoDetailScreen

        def _push() -> None:
            screen = self.screen
            if isinstance(screen, RepoDetailScreen):
                screen._launch_action(action_key)

        return _push

    def _pop(self) -> None:
        self.app.pop_screen()

    def _clear_chat(self) -> None:
        from tui.screens.chat import ChatScreen
        screen = self.screen
        if isinstance(screen, ChatScreen):
            screen.action_clear_chat()


# (action key, human-readable label) — mirrors the menu in RepoDetailScreen.
_REPO_ACTIONS = [
    ("analysis", "Analysis"),
    ("pulls", "Pull Requests"),
    ("autofix", "Auto-Fix"),
    ("diagram", "Architecture Diagram"),
    ("chat", "Chat"),
]