"""
app.py — Textual App root for gitcat TUI.

Defines the top-level App, global key bindings, and dark theme.
All screen routing is driven by screen push/pop from child screens.
"""
from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Ensure backend/ is importable when this module is imported directly.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import CommandPalette, Provider

from tui.core import GitcatCore
from tui.screens.repos import ReposScreen
from tui.commands import GitcatCommandProvider


class GitcatApp(App):
    """Root Textual application for gitcat."""

    TITLE = "gitcat"
    SUB_TITLE = "AI-powered GitHub assistant"

    # Command palette (ctrl+p) providers.
    COMMANDS = {GitcatCommandProvider}

    # No external CSS file — keep all styling inline / default dark theme.
    CSS_PATH = None

    # Minimal inline CSS for status bar colour consistency.
    CSS = """
    Screen {
        background: $surface;
    }
    Footer {
        background: $panel;
    }
    """

    BINDINGS = [
        Binding("ctrl+p", "command_palette", "Commands", show=True, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
    ]

    def __init__(self, core: GitcatCore, **kwargs) -> None:
        super().__init__(**kwargs)
        self.core = core
        # Force dark mode.
        self.dark = True

    def on_mount(self) -> None:
        """Push the initial repos screen when the app starts."""
        self.push_screen(ReposScreen(core=self.core))

    def compose(self) -> ComposeResult:
        # The app shell is empty; screens provide all widgets.
        return iter([])
