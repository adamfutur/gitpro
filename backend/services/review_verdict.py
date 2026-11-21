"""Parse AI review verdicts without letting malformed text approve a PR."""
import json
import re

VERDICT_BLOCK_RE = re.compile(r"```gitcat-verdict\s*(\{.*?\})\s*```", re.DOTALL)
INCONCLUSIVE = {
    "status": "inconclusive",
    "reason": "Review verdict unavailable; manual review required.",
}


def extract_verdict(review_text: str) -> tuple[str, dict]:
    """Fail closed on missing, invalid or unexpected LLM verdict JSON."""
    match = VERDICT_BLOCK_RE.search(review_text)
    if not match:
        return review_text.strip(), dict(INCONCLUSIVE)
    body = (review_text[:match.start()] + review_text[match.end():]).strip()
    try:
        verdict = json.loads(match.group(1))
        if not isinstance(verdict, dict) or verdict.get("status") not in ("pass", "fail"):
            return body, dict(INCONCLUSIVE)
        reason = verdict.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            return body, dict(INCONCLUSIVE)
        return body, {"status": verdict["status"], "reason": reason[:140]}
    except (ValueError, TypeError):
        return body, dict(INCONCLUSIVE)
