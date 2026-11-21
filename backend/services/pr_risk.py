"""Deterministic, explainable change-risk signals for gitcat PR reviews.

Not a security scanner or a prediction of defects: scores are review-priority
heuristics calculated entirely from GitHub's changed-file metadata.
"""
from __future__ import annotations

import math
import re
from pathlib import PurePosixPath

TEST_RE = re.compile(r"(^|/)(tests?|__tests__|specs?)(/|$)|(^|[._-])(test|spec)[._-]", re.I)
SENSITIVE_RE = re.compile(
    r"(^|/)(auth|authentication|security|permissions?|payments?|billing|"
    r"migrations?|database|infra|terraform|workflows)(/|$)|"
    r"(^|/)(Dockerfile|docker-compose[^/]*|\.env[^/]*|"
    r"package-lock\.json|requirements[^/]*\.txt)$", re.I
)
GENERATED_RE = re.compile(
    r"(^|/)(dist|build|vendor|generated|node_modules)(/|$)|"
    r"(\.min\.(js|css)$|\.lock$|package-lock\.json$)", re.I
)


def _is_test(path: str) -> bool:
    return bool(TEST_RE.search(path))


def analyze_pr_risk(files: list[dict], reviewed_file_limit: int = 20,
                    patch_char_limit: int = 3000) -> dict:
    """Return stable risk findings and visibility limitations for a PR.

    Scores range from 0..100, higher means *prioritize review*, not
    probability of a bug. Never read source code or send metadata to AI.
    """
    items = []
    total = len(files)
    has_test_changes = any(_is_test(str(f.get("filename", ""))) for f in files)
    total_lines = 0
    for entry in files:
        path = str(entry.get("filename") or "")
        additions = max(0, int(entry.get("additions") or 0))
        deletions = max(0, int(entry.get("deletions") or 0))
        churn = additions + deletions
        total_lines += churn
        reasons = []
        if SENSITIVE_RE.search(path):
            reasons.append("Sensitive or infrastructure-related path")
        if churn >= 300:
            reasons.append("Large change (300+ lines)")
        elif churn >= 100:
            reasons.append("Substantial change (100+ lines)")
        if entry.get("status") in ("removed", "renamed"):
            reasons.append("File removed or renamed")
        if GENERATED_RE.search(path):
            reasons.append("Generated or dependency-managed file")
        score = min(100, round(
            10 + (30 if SENSITIVE_RE.search(path) else 0)
            + min(35, 9 * math.log2(churn + 1))
            + (12 if entry.get("status") in ("removed", "renamed") else 0)
            - (18 if _is_test(path) else 0)
            - (18 if GENERATED_RE.search(path) else 0)
        ))
        items.append({
            "path": path,
            "score": max(0, score),
            "level": "high" if score >= 65 else "medium" if score >= 35 else "low",
            "changes": churn,
            "reasons": reasons or ["Limited change surface"],
        })

    items.sort(key=lambda item: (-item["score"], item["path"]))
    source_changes = [f for f in files
                      if not _is_test(str(f.get("filename", "")))
                      and not GENERATED_RE.search(str(f.get("filename", "")))]
    # This is a reminder to check tests, not an assertion that tests are missing.
    suggestions = []
    if source_changes and not has_test_changes:
        suggestions.append("No test files changed: check whether existing tests cover the behavior.")
    if any(SENSITIVE_RE.search(str(f.get("filename", ""))) for f in files):
        suggestions.append("Verify authorization, secrets, failure modes and rollback paths.")
    if total_lines >= 400:
        suggestions.append("Consider splitting or reviewing the large diff in smaller sections.")
    if any(f.get("status") == "removed" for f in files):
        suggestions.append("Check callers and compatibility for removed files.")
    if not suggestions:
        suggestions.append("Run relevant tests and inspect the highest-priority files first.")

    # The current AI reviewer reads only the first N files and truncates patches.
    evaluated = files[:max(0, reviewed_file_limit)]
    patched = sum(1 for f in evaluated if f.get("patch") is not None)
    truncated = sum(1 for f in evaluated
                    if isinstance(f.get("patch"), str)
                    and len(f["patch"]) > patch_char_limit)
    coverage = {
        "changed_files": total,
        "files_selected_for_ai": len(evaluated),
        "files_with_patches": patched,
        "files_with_truncated_patches": truncated,
        "files_not_selected": max(0, total - len(evaluated)),
        "complete": total <= reviewed_file_limit and patched == total and truncated == 0,
    }
    top_score = items[0]["score"] if items else 0
    return {
        "score": top_score,
        "level": "high" if top_score >= 65 else "medium" if top_score >= 35 else "low",
        "method": "Transparent file-path and change-size heuristics; not an AI verdict or vulnerability scan.",
        "files": items[:8],
        "test_files_changed": has_test_changes,
        "review_checklist": suggestions,
        "coverage": coverage,
    }
