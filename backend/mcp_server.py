"""
gitcat MCP Server
-----------------
Exposes gitcat backend services as MCP tools over stdio transport.

Usage:
    GITHUB_TOKEN=ghp_... GEMINI_API_KEY=... python mcp_server.py

All tools use the single GITHUB_TOKEN read from the environment at startup.
"""

import sys
import os

# Ensure the backend package root is on the path so that service imports work.
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import json
import datetime

# ---------------------------------------------------------------------------
# Environment / auth
# ---------------------------------------------------------------------------

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if not GITHUB_TOKEN:
    raise EnvironmentError(
        "GITHUB_TOKEN environment variable is required but was not set. "
        "Export a valid GitHub personal-access token before starting the MCP server."
    )

# ---------------------------------------------------------------------------
# Service imports (after sys.path is set)
# ---------------------------------------------------------------------------

from services.github_service import (
    get_user_repos,
    get_repo_details,
    get_repo_readme,
    get_repo_commits,
    get_repo_prs,
    get_repo_files,
    get_file_content,
    list_pull_requests as _list_pull_requests_svc,
)
from services.repo_reader import fetch_repo_tree_recursive
from services.gemini_service import call_gemini, call_gemini_with_tools
from services.nlp_analyzer import analyze_code_file, generate_nlp_summary
from services.anomaly_detector import detect_code_anomalies
from services.kpi_calculator import calculate_kpis
from services.pr_review import build_pr_review
from services.auto_fix import scan_for_fixes, create_fix_pr
from services.architecture import generate_architecture_diagram

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

# Cache of the last scan_for_fixes result per repo_id (includes new_content).
_fix_scan_cache: dict[int, dict] = {}

# In-memory chat sessions keyed by session_id string.
_chat_sessions: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

# mcp 2.x renamed FastMCP to MCPServer; support both majors.
try:
    from mcp.server.mcpserver import MCPServer as FastMCP  # mcp >= 2.0
except ImportError:  # mcp < 2.0
    from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]

mcp = FastMCP("gitcat")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _err(msg: str) -> str:
    """Return a JSON error string."""
    return json.dumps({"error": msg})


# ---------------------------------------------------------------------------
# Tool 1 — list_repos
# ---------------------------------------------------------------------------

@mcp.tool()
def list_repos() -> str:
    """List all GitHub repositories accessible with the configured token.

    Returns a JSON array where each element contains:
    id, name, full_name, description, language, stars, forks, private.
    """
    try:
        repos = get_user_repos(GITHUB_TOKEN)
        result = []
        for repo in repos:
            result.append({
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "private": repo.get("private", False),
            })
        return json.dumps(result)
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 2 — get_repo_health
# ---------------------------------------------------------------------------

@mcp.tool()
def get_repo_health(repo_id: int) -> str:
    """Run a full AI-powered health analysis on a repository.

    Fetches repo metadata, README, up to 25 source files, recent commits and
    pull requests, then calls the Gemini AI for a comprehensive code review.
    Also computes NLP-based KPIs and detects code anomalies.

    Args:
        repo_id: The numeric GitHub repository ID.

    Returns a JSON object with keys: repo_id, repo_name, repo_full_name,
    analysis, kpis, anomalies, generated_at, status.
    """
    try:
        # 1. Repo details
        repo = get_repo_details(GITHUB_TOKEN, repo_id)
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        default_branch = repo.get("default_branch", "main")

        # 2. Build analysis prompt
        analysis_prompt = (
            f"Analyze this GitHub repository comprehensively:\n\n"
            f"Repository: {repo['name']}\n"
            f"Description: {repo.get('description', 'No description')}\n"
            f"Language: {repo.get('language', 'Unknown')}\n"
            f"Stars: {repo.get('stargazers_count', 0)}\n"
            f"Forks: {repo.get('forks_count', 0)}\n"
        )

        # 3. README
        readme = get_repo_readme(GITHUB_TOKEN, owner, repo_name)
        if readme:
            analysis_prompt += f"\nREADME:\n{readme[:3000]}\n"

        # 4. Fetch up to 25 files and run NLP analysis
        important_files = fetch_repo_tree_recursive(
            GITHUB_TOKEN, owner, repo_name,
            max_files=25, branch=default_branch,
        )
        nlp_analyses = []
        if important_files:
            analysis_prompt += f"\n\n=== CODE FILES ({len(important_files)} files analyzed) ===\n"
            for file_data in important_files:
                analysis_prompt += f"\n--- {file_data['path']} ---\n{file_data['content'][:4000]}\n"
                nlp_result = analyze_code_file(file_data["name"], file_data["content"], fast_mode=False)
                nlp_analyses.append(nlp_result)

        # 5. NLP summary
        if nlp_analyses:
            nlp_summary = generate_nlp_summary(nlp_analyses)
            analysis_prompt += f"\n\n=== DETAILED NLP CODE ANALYSIS ===\n{nlp_summary}\n"

        # 6. Commits
        commits = get_repo_commits(GITHUB_TOKEN, owner, repo_name)
        if commits:
            analysis_prompt += "\n\nRecent Commits:\n"
            for c in commits[:10]:
                msg = c["commit"]["message"].split("\n")[0]
                author = c["commit"]["author"]["name"]
                date = c["commit"]["author"]["date"]
                analysis_prompt += f"- {msg} (by {author}, {date})\n"

        # 7. Pull requests
        prs = get_repo_prs(GITHUB_TOKEN, owner, repo_name)
        if prs:
            analysis_prompt += "\n\nRecent Pull Requests:\n"
            for pr in prs[:10]:
                analysis_prompt += f"- PR #{pr['number']}: {pr['title']} (State: {pr['state']})\n"

        # 8. AI analysis prompt suffix
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
        analysis_result = call_gemini(analysis_prompt)

        # 9. Anomaly detection
        anomalies = detect_code_anomalies(nlp_analyses)

        # 10. KPI calculation
        kpis = calculate_kpis(nlp_analyses, repo, commits, prs)

        result = {
            "repo_id": repo_id,
            "repo_name": repo["name"],
            "repo_full_name": repo["full_name"],
            "analysis": analysis_result,
            "kpis": kpis,
            "anomalies": anomalies,
            "generated_at": datetime.datetime.utcnow().isoformat(),
            "status": "completed",
        }
        return json.dumps(result)
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 3 — list_pull_requests
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pull_requests(repo_id: int, state: str = "open") -> str:
    """List pull requests for a repository.

    Args:
        repo_id: The numeric GitHub repository ID.
        state:   PR state filter — 'open', 'closed', or 'all'. Defaults to 'open'.

    Returns a JSON array of PR objects.
    """
    try:
        repo = get_repo_details(GITHUB_TOKEN, repo_id)
        owner = repo["owner"]["login"]
        repo_name = repo["name"]
        prs = _list_pull_requests_svc(GITHUB_TOKEN, owner, repo_name, state=state)
        return json.dumps(prs)
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 4 — review_pull_request
# ---------------------------------------------------------------------------

@mcp.tool()
def review_pull_request(repo_id: int, pr_number: int) -> str:
    """Run an AI-powered code review on a pull request.

    Args:
        repo_id:    The numeric GitHub repository ID.
        pr_number:  The pull request number to review.

    Returns a JSON object containing the full review text and a verdict with
    keys: status and reason.
    """
    try:
        result_dict, _owner, _repo_name = build_pr_review(
            GITHUB_TOKEN, repo_id, pr_number, on_stage=None
        )
        return json.dumps(result_dict)
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 5 — scan_auto_fix
# ---------------------------------------------------------------------------

@mcp.tool()
def scan_auto_fix(repo_id: int) -> str:
    """Scan a repository for automatically fixable issues.

    Runs static analysis to identify code issues that can be auto-patched.
    The full scan result (including new file contents) is stored in an
    internal cache so that apply_auto_fix can use it immediately after.

    Args:
        repo_id: The numeric GitHub repository ID.

    Returns a JSON object with keys: repo_id, branch, fixes — where each fix
    contains: file, description, diff (new_content is omitted for readability).
    """
    try:
        scan_result = scan_for_fixes(GITHUB_TOKEN, repo_id, on_stage=None)

        # Cache the full result (including new_content) for apply_auto_fix.
        _fix_scan_cache[repo_id] = scan_result

        # Build a readable copy without new_content.
        readable_fixes = []
        for fix in scan_result.get("fixes", []):
            readable_fixes.append({
                "file": fix.get("file"),
                "description": fix.get("description"),
                "diff": fix.get("diff"),
            })

        return json.dumps({
            "repo_id": scan_result.get("repo_id"),
            "branch": scan_result.get("branch"),
            "fixes": readable_fixes,
        })
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 6 — apply_auto_fix
# ---------------------------------------------------------------------------

@mcp.tool()
def apply_auto_fix(repo_id: int, file_paths: list[str] | None = None) -> str:
    """Apply cached auto-fix suggestions by opening a pull request.

    You must call scan_auto_fix first to populate the cache for this repo.

    Args:
        repo_id:    The numeric GitHub repository ID.
        file_paths: Optional list of file paths to apply. If None or empty,
                    ALL fixes from the last scan are applied.

    Returns a JSON object with a pr_url key on success.
    """
    if repo_id not in _fix_scan_cache:
        return _err(
            f"No cached scan found for repo_id={repo_id}. "
            "Run scan_auto_fix first."
        )

    try:
        scan_result = _fix_scan_cache[repo_id]
        all_fixes = scan_result.get("fixes", [])
        base_branch = scan_result.get("branch", "main")

        if file_paths:
            selected_fixes = [
                f for f in all_fixes if f.get("file") in file_paths
            ]
            if not selected_fixes:
                return _err(
                    f"None of the requested file_paths were found in the cached scan. "
                    f"Available: {[f.get('file') for f in all_fixes]}"
                )
        else:
            selected_fixes = all_fixes

        # create_fix_pr expects each fix to have file, description, new_content.
        pr_data = create_fix_pr(
            GITHUB_TOKEN, repo_id, base_branch, selected_fixes
        )
        return json.dumps({"pr_url": pr_data.get("html_url")})
    except ValueError as exc:
        return _err(str(exc))
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 7 — generate_diagram
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_diagram(repo_id: int) -> str:
    """Generate a Mermaid architecture diagram for a repository.

    Args:
        repo_id: The numeric GitHub repository ID.

    Returns the raw Mermaid diagram source string (not JSON).
    """
    try:
        result = generate_architecture_diagram(GITHUB_TOKEN, repo_id, on_stage=None)
        return result.get("diagram", "")
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Tool 8 — chat_with_repo
# ---------------------------------------------------------------------------

@mcp.tool()
def chat_with_repo(repo_id: int, message: str, session_id: str = "") -> str:
    """Chat with an AI assistant about a specific repository.

    Maintains conversation history across calls via session_id. If session_id
    is empty, a new session is created and its ID is returned in the response.

    The assistant has on-demand tools to read the README, list and read files,
    and view recent commits and pull requests.

    Args:
        repo_id:    The numeric GitHub repository ID.
        message:    The user message / question.
        session_id: Optional existing session ID. Leave empty to start fresh.

    Returns a JSON object with keys: session_id, response.
    """
    try:
        # Create a new session if needed.
        if not session_id or session_id not in _chat_sessions:
            session_id = str(int(datetime.datetime.utcnow().timestamp() * 1000))
            _chat_sessions[session_id] = {
                "repo_id": repo_id,
                "messages": [],
                "created_at": datetime.datetime.utcnow().isoformat(),
            }

        session = _chat_sessions[session_id]

        # Build system context.
        context = (
            "You are an expert AI coding assistant helping developers understand their GitHub "
            "repositories. You have tools to look up the README, list and read files, and view "
            "recent commits and pull requests. Only call a tool when the question actually "
            "requires that information."
        )

        owner = repo_name = None
        try:
            repo = get_repo_details(GITHUB_TOKEN, repo_id)
            owner = repo["owner"]["login"]
            repo_name = repo["name"]

            context += "\n\n=== REPOSITORY ===\n"
            context += f"Name: {repo['name']}\n"
            context += f"Description: {repo.get('description', 'No description')}\n"
            context += f"Language: {repo.get('language', 'Unknown')}\n"
            context += f"Stars: {repo.get('stargazers_count', 0)}\n"
            context += f"Forks: {repo.get('forks_count', 0)}\n"
            context += f"Open Issues: {repo.get('open_issues_count', 0)}\n"
        except Exception as repo_exc:
            context += f"\n[Warning: could not fetch repo details — {repo_exc}]\n"

        # Append recent conversation history (last 5 exchanges).
        if session["messages"]:
            context += "\n=== CONVERSATION HISTORY ===\n"
            for msg in session["messages"][-5:]:
                context += f"{msg['role']}: {msg['content']}\n"

        # Define on-demand tools available to the model.
        tools = []
        if owner and repo_name:
            def get_readme() -> str:
                """Get the repository's README file content."""
                readme = get_repo_readme(GITHUB_TOKEN, owner, repo_name)
                return readme[:4000] if readme else "No README found."

            def list_files(path: str = "") -> str:
                """List files and folders in the repository at the given path. Use an empty path for the repository root."""
                files = get_repo_files(GITHUB_TOKEN, owner, repo_name, path)
                if not files:
                    return f"No files found at path '{path}'."
                return "\n".join(f"{f['type']}: {f['path']}" for f in files)

            def read_file(path: str) -> str:
                """Get the content of a specific file in the repository, given its path."""
                content = get_file_content(GITHUB_TOKEN, owner, repo_name, path)
                return content[:4000] if content else f"Could not read file: {path}"

            def get_recent_commits() -> str:
                """Get the 5 most recent commits to the repository."""
                commits = get_repo_commits(GITHUB_TOKEN, owner, repo_name)
                if not commits:
                    return "No commits found."
                return "\n".join(
                    f"- {c['commit']['message'].splitlines()[0]} "
                    f"(by {c['commit']['author']['name']}, {c['commit']['author']['date']})"
                    for c in commits[:5]
                )

            def get_pull_requests() -> str:
                """Get the 5 most recent pull requests for the repository."""
                prs = get_repo_prs(GITHUB_TOKEN, owner, repo_name)
                if not prs:
                    return "No pull requests found."
                return "\n".join(
                    f"- PR #{pr['number']}: {pr['title']} "
                    f"(state: {pr['state']}, author: {pr['user']['login']})"
                    for pr in prs[:5]
                )

            tools = [get_readme, list_files, read_file, get_recent_commits, get_pull_requests]

        # Call the AI.
        if tools:
            ai_response = call_gemini_with_tools(message, tools, context)
        else:
            ai_response = call_gemini(message, context)

        # Persist messages to session history.
        now = datetime.datetime.utcnow().isoformat()
        session["messages"].append({"role": "user", "content": message, "created_at": now})
        session["messages"].append({"role": "assistant", "content": ai_response, "created_at": now})

        return json.dumps({"session_id": session_id, "response": ai_response})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
