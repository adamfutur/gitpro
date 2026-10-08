"""Headless smoke test for the gitcat command palette.

Run: python backend/tui/test_commands.py
"""
from __future__ import annotations

import asyncio
import os
import sys

# Make `tui` importable regardless of CWD (backend/ is the package root).
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from textual.command import CommandPalette  # noqa: E402
from textual.command import CommandList  # noqa: E402
from textual.widgets import ListView  # noqa: E402

from tui.app import GitcatApp  # noqa: E402
from tui.core import GitcatCore  # noqa: E402


async def open_palette(app: GitcatApp, query: str = "") -> list[str]:
    # action_command_palette() is synchronous in Textual >= 5.
    app.action_command_palette()
    await app.pilot.pause()
    assert CommandPalette.is_open(app), "palette did not open"
    # Let the palette's _gather_commands worker finish before reading options.
    await app.workers.wait_for_complete()
    await app.pilot.pause()
    if query:
        for ch in query:
            await app.pilot.press(ch)
        await app.workers.wait_for_complete()
        await app.pilot.pause()
    # The palette is itself the active screen.
    option_list = app.screen.query_one(CommandList)
    labels = [str(opt.prompt) for opt in option_list.options]
    await app.pilot.press("escape")
    await app.pilot.pause()
    return labels


async def main() -> None:
    core = GitcatCore(github_token="dummy", user={"login": "tester"})
    app = GitcatApp(core=core)

    async with app.run_test() as pilot:
        app.pilot = pilot  # type: ignore[attr-defined]

        labels = await open_palette(app)
        print("REPOS discovery:", labels)
        assert any("Refresh" in l for l in labels), "missing Refresh"
        assert any("Quit" in l for l in labels), "missing Quit"

        # Push a repo detail screen so we can test the action commands.
        from tui.screens.repos import ReposScreen
        repos = app.screen
        assert isinstance(repos, ReposScreen), f"expected ReposScreen, got {repos!r}"
        repos._all_repos = [{"id": 1, "name": "demo", "full_name": "tester/demo"}]
        repos._on_repos_loaded(repos._all_repos)
        await pilot.pause()
        # Focus the list and highlight the first item so "enter" selects it.
        repo_list = repos.query_one("#repo-list", ListView)
        repo_list.focus()
        repo_list.index = 0
        await pilot.pause()
        await pilot.press("enter")  # select first repo → RepoDetailScreen
        await pilot.pause()

        labels = await open_palette(app)
        print("REPO-DETAIL discovery:", labels)
        for expected in ("Analysis", "Pull Requests", "Auto-Fix", "Architecture Diagram", "Chat", "Back"):
            assert any(expected in l for l in labels), f"missing {expected}"

        # Filter to Analysis and select it → pushes AnalysisScreen.
        await open_palette(app, "Analysis")
        await pilot.press("enter")
        await pilot.pause()

        labels = await open_palette(app)
        print("FEATURE discovery:", labels)
        assert any("Back" in l for l in labels), "missing Back on feature screen"

    print("OK — command palette works end-to-end")


if __name__ == "__main__":
    asyncio.run(main())