"""
screens/analysis.py — Repository health analysis screen.

Runs the full analysis pipeline (same as routes/repos.py _run_analysis) in a
background thread and displays:
  - Live stage progress messages while running.
  - KPI scores table once finished.
  - Anomaly count.
  - Full scrollable AI analysis text.

Press q to go back.
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
from textual.widgets import Footer, Header, Label, LoadingIndicator, Static
from textual.scroll_view import ScrollView

from tui.core import GitcatCore


class AnalysisScreen(Screen):
    """Full analysis pipeline screen."""

    BINDINGS = [
        Binding("q", "go_back", "Back", show=True),
    ]

    CSS = """
    #stage-label {
        height: 1;
        padding: 0 2;
        color: $text-muted;
    }
    LoadingIndicator {
        height: 3;
    }
    #result-area {
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
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
        yield LoadingIndicator(id="spinner")
        yield Static("[dim]Initialising…[/dim]", id="stage-label", markup=True)
        yield Static("", id="result-area", markup=True, expand=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        repo = self.repo
        self.title = f"Analysis — {repo.get('name', '')}"
        self.sub_title = f"@{self.core.login}"
        self._run_analysis()

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------

    @work(thread=True)
    def _run_analysis(self) -> None:
        def on_stage(message: str) -> None:
            self.app.call_from_thread(self._update_stage, message)

        try:
            on_stage("Fetching repository details…")
            from services.github_service import (
                get_repo_details,
                get_repo_readme,
                get_repo_commits,
                get_repo_prs,
            )
            from services.repo_reader import fetch_repo_tree_recursive
            from services.gemini_service import call_gemini
            from services.nlp_analyzer import analyze_code_file, generate_nlp_summary
            from services.anomaly_detector import detect_code_anomalies
            from services.kpi_calculator import calculate_kpis

            repo = get_repo_details(self.core.github_token, self.repo["id"])
            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            analysis_prompt = (
                f"Analyze this GitHub repository comprehensively:\n\n"
                f"Repository: {repo['name']}\n"
                f"Description: {repo.get('description', 'No description')}\n"
                f"Language: {repo['language']}\n"
                f"Stars: {repo.get('stargazers_count', 0)}\n"
                f"Forks: {repo.get('forks_count', 0)}\n"
            )

            on_stage("Fetching README…")
            readme = get_repo_readme(self.core.github_token, owner, repo_name)
            if readme:
                analysis_prompt += f"\nREADME:\n{readme[:3000]}\n"

            on_stage("Walking the repository tree…")
            important_files = fetch_repo_tree_recursive(
                self.core.github_token,
                owner,
                repo_name,
                max_files=25,
                branch=repo.get("default_branch", "main"),
            )
            nlp_analyses: list = []

            if important_files:
                on_stage(f"Running NLP analysis on {len(important_files)} files…")
                analysis_prompt += f"\n\n=== CODE FILES ({len(important_files)} files analyzed) ===\n"
                for file_data in important_files:
                    analysis_prompt += f"\n--- {file_data['path']} ---\n{file_data['content'][:4000]}\n"
                    nlp_result = analyze_code_file(
                        file_data["name"], file_data["content"], fast_mode=False
                    )
                    nlp_analyses.append(nlp_result)

            if nlp_analyses:
                nlp_summary = generate_nlp_summary(nlp_analyses)
                analysis_prompt += f"\n\n=== DETAILED NLP CODE ANALYSIS ===\n{nlp_summary}\n"

            on_stage("Fetching commits and PRs…")
            commits = get_repo_commits(self.core.github_token, owner, repo_name)
            if commits:
                analysis_prompt += "\n\nRecent Commits:\n"
                for c in commits[:10]:
                    msg = c["commit"]["message"].split("\n")[0]
                    author = c["commit"]["author"]["name"]
                    date = c["commit"]["author"]["date"]
                    analysis_prompt += f"- {msg} (by {author}, {date})\n"

            prs = get_repo_prs(self.core.github_token, owner, repo_name)
            if prs:
                analysis_prompt += "\n\nRecent Pull Requests:\n"
                for pr in prs[:10]:
                    analysis_prompt += (
                        f"- PR #{pr['number']}: {pr['title']} (State: {pr['state']})\n"
                    )

            analysis_prompt += """

Based on the comprehensive analysis above, provide a detailed evaluation including:
1. Code Quality Assessment (score 1-10 with detailed justification)
2. Architecture Overview (patterns, structure, design decisions)
3. Security Considerations (vulnerabilities, best practices)
4. Performance Insights (bottlenecks, optimization opportunities)
5. Maintainability Assessment (technical debt, documentation quality)
6. Suggested Improvements (prioritized list addressing code smells)
7. Technology Stack Analysis (dependencies, versions, compatibility)
8. Team Collaboration Indicators (commit patterns, PR quality)
"""

            on_stage("Generating AI code review with Gemini…")
            analysis_result = call_gemini(analysis_prompt)

            on_stage("Running ML anomaly detection…")
            anomalies = detect_code_anomalies(nlp_analyses)

            on_stage("Calculating repository KPIs…")
            kpis = calculate_kpis(nlp_analyses, repo, commits, prs)

            result = {
                "repo_id": self.repo["id"],
                "repo_name": repo["name"],
                "repo_full_name": repo["full_name"],
                "analysis": analysis_result,
                "kpis": kpis,
                "anomalies": anomalies,
                "generated_at": datetime.datetime.utcnow().isoformat(),
                "status": "completed",
            }
            self.app.call_from_thread(self._on_done, result)

        except Exception as exc:
            self.app.call_from_thread(self._on_error, str(exc))

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _update_stage(self, message: str) -> None:
        self.query_one("#stage-label", Static).update(f"[dim]{message}[/dim]")

    def _on_done(self, result: dict) -> None:
        # Hide spinner + stage label.
        self.query_one(LoadingIndicator).display = False
        self.query_one("#stage-label", Static).display = False

        kpis: dict = result.get("kpis") or {}
        anomalies = result.get("anomalies") or []
        analysis_text: str = result.get("analysis") or ""

        lines: list[str] = []

        # KPI table
        lines.append("[bold]── KPIs ──────────────────────────────[/bold]")
        kpi_keys = [
            ("quality_score", "Quality"),
            ("maintainability_score", "Maintainability"),
            ("productivity_score", "Productivity"),
            ("security_score", "Security"),
        ]
        found_any = False
        for key, label in kpi_keys:
            val = kpis.get(key)
            if val is not None:
                found_any = True
                colour = "green" if float(val) >= 7 else "yellow" if float(val) >= 4 else "red"
                lines.append(f"  {label:<20}[{colour}]{val:.1f}[/{colour}] / 10")
        if not found_any:
            for key, val in kpis.items():
                if isinstance(val, (int, float)):
                    lines.append(f"  {key:<20}{val}")

        # Anomalies
        lines.append("")
        anom_count = len(anomalies) if isinstance(anomalies, list) else 0
        colour = "red" if anom_count > 0 else "green"
        lines.append(
            f"[bold]── Anomalies ─────────────────────────[/bold]  [{colour}]{anom_count} detected[/{colour}]"
        )

        # AI Analysis
        lines.append("")
        lines.append("[bold]── AI Analysis ───────────────────────[/bold]")
        lines.append("")
        # Escape any Rich markup in the raw text to avoid rendering errors.
        safe_analysis = analysis_text.replace("[", "\\[")
        lines.append(safe_analysis)

        self.query_one("#result-area", Static).update("\n".join(lines))

    def _on_error(self, msg: str) -> None:
        self.query_one(LoadingIndicator).display = False
        self.query_one("#stage-label", Static).display = False
        self.query_one("#result-area", Static).update(
            f"[red]Analysis failed:[/red]\n{msg}"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_go_back(self) -> None:
        self.app.pop_screen()
