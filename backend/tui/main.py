"""
main.py — gitcat TUI entrypoint.

Run as:
    python backend/tui/main.py
    python -m backend.tui   (requires backend/ on PYTHONPATH)

Steps:
1. Load GITHUB_TOKEN and GEMINI_API_KEY from environment / .env file.
2. Validate the token by calling get_github_user.
3. Build a GitcatCore instance.
4. Launch the Textual App.
"""
from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# Ensure backend/ is importable regardless of where the script is launched from.
# ---------------------------------------------------------------------------
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
_BACKEND_DIR = os.path.normpath(_BACKEND_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Load .env before anything else (dotenv is a no-op if the file is absent).
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, "..", ".env"))  # repo root .env
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))  # backend .env if exists
except ImportError:
    pass  # dotenv not installed — fall back to real env vars

# ---------------------------------------------------------------------------
# Validate required environment variables.
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_ACCESS_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

_missing: list[str] = []
if not GITHUB_TOKEN:
    _missing.append("GITHUB_TOKEN  (or GITHUB_ACCESS_TOKEN)")
if not GEMINI_API_KEY:
    _missing.append("GEMINI_API_KEY")

if _missing:
    print("\n[gitcat] ✗  Missing required environment variables:\n")
    for var in _missing:
        print(f"    {var}")
    print(
        "\nSet them in a .env file at the project root or export them before running.\n"
        "Example:\n"
        "    export GITHUB_TOKEN=ghp_...\n"
        "    export GEMINI_API_KEY=AIza...\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Set GEMINI_API_KEY so gemini_service picks it up (it reads os.environ).
# ---------------------------------------------------------------------------
os.environ.setdefault("GEMINI_API_KEY", GEMINI_API_KEY)

# ---------------------------------------------------------------------------
# Validate GitHub token.
# ---------------------------------------------------------------------------
from services.github_service import get_github_user  # noqa: E402

print("[gitcat] Validating GitHub token…")
try:
    _user = get_github_user(GITHUB_TOKEN)
    if "login" not in _user:
        raise ValueError(f"Unexpected response: {_user}")
except Exception as exc:
    print(f"\n[gitcat] ✗  GitHub token validation failed: {exc}\n")
    sys.exit(1)

print(f"[gitcat] ✓  Authenticated as @{_user['login']}")

# ---------------------------------------------------------------------------
# Build shared state and launch the app.
# ---------------------------------------------------------------------------
from tui.core import GitcatCore  # noqa: E402
from tui.app import GitcatApp    # noqa: E402

core = GitcatCore(github_token=GITHUB_TOKEN, user=_user)

def main() -> None:
    app = GitcatApp(core=core)
    app.run()


if __name__ == "__main__":
    main()
