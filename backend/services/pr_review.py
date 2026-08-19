import datetime
import json
import re
from services.github_service import get_repo_details, get_pr_details, get_pr_files
from services.gemini_service import call_gemini

MAX_REVIEWED_FILES = 20
MAX_PATCH_CHARS = 3000

VERDICT_BLOCK_RE = re.compile(r"```gitcat-verdict\s*(\{.*?\})\s*```", re.DOTALL)

DEFAULT_VERDICT = {'status': 'pass', 'reason': 'No blocking issues identified.'}

def _extract_verdict(review_text):
    """
    Pulls the trailing ```gitcat-verdict fenced JSON block out of the review text (so it
    isn't shown as raw JSON to the reader) and returns (clean_review_text, verdict_dict).
    Falls back to a "pass" verdict if the block is missing or malformed — a parsing bug
    should never silently block someone's PR (fail-open, not fail-closed).
    """
    match = VERDICT_BLOCK_RE.search(review_text)
    if not match:
        return review_text.strip(), dict(DEFAULT_VERDICT)

    clean_text = (review_text[:match.start()] + review_text[match.end():]).strip()
    try:
        verdict = json.loads(match.group(1))
        status = verdict.get('status')
        if status not in ('pass', 'fail'):
            return clean_text, dict(DEFAULT_VERDICT)
        return clean_text, {'status': status, 'reason': verdict.get('reason', '')[:300]}
    except Exception as e:
        print(f"Failed to parse gitcat-verdict block: {e}")
        return clean_text, dict(DEFAULT_VERDICT)

def build_pr_review(github_token, repo_id, pr_number, on_stage=None):
    """
    Fetches a pull request's diff and asks Gemini for a focused review of just the
    change (not the whole repo). Shared by the manual "Review this PR" flow and the
    webhook-triggered auto-review flow.

    Returns (result_dict, owner, repo_name).
    """
    def stage(message):
        if on_stage:
            on_stage(message)

    stage('Fetching pull request details...')
    repo = get_repo_details(github_token, repo_id)
    owner = repo['owner']['login']
    repo_name = repo['name']

    pr = get_pr_details(github_token, owner, repo_name, pr_number)
    if not pr:
        raise ValueError('Pull request not found')

    stage('Fetching changed files...')
    files = get_pr_files(github_token, owner, repo_name, pr_number)

    total_additions = sum(f.get('additions', 0) for f in files)
    total_deletions = sum(f.get('deletions', 0) for f in files)

    stage(f'Analyzing {min(len(files), MAX_REVIEWED_FILES)} changed files...')
    prompt = f"""You are an expert code reviewer. Review this GitHub pull request, focusing specifically on the changes it introduces — not the whole repository.

Pull Request #{pr_number}: {pr['title']}
Author: {pr['user']['login']}
Description: {pr.get('body') or 'No description provided.'}
Base: {pr['base']['ref']} <- Head: {pr['head']['ref']}
Files changed: {len(files)} (+{total_additions} / -{total_deletions})

=== CHANGED FILES ===
"""
    for f in files[:MAX_REVIEWED_FILES]:
        patch = f.get('patch')
        prompt += f"\n--- {f['filename']} ({f['status']}, +{f.get('additions', 0)}/-{f.get('deletions', 0)}) ---\n"
        prompt += f"{patch[:MAX_PATCH_CHARS]}\n" if patch else "(diff not available — binary or too large)\n"

    prompt += """

Provide a focused code review including:
1. A short summary of what this PR does
2. Potential bugs or correctness issues introduced by this diff
3. Code quality / style concerns in the changed lines
4. Security considerations in the diff
5. Missing tests or documentation for the change
6. Specific, actionable suggestions, referencing file names where relevant

After the written review, end with a final block in EXACTLY this format (for automated parsing —
nothing after it):

```gitcat-verdict
{"status": "pass", "reason": "one sentence explaining the verdict"}
```

Use "status": "fail" ONLY for genuine blocking problems — security vulnerabilities, correctness
bugs that would break functionality, or severe regressions. Use "pass" for everything else,
including files with only minor style suggestions or nitpicks.
"""

    stage('Generating AI review with Gemini...')
    raw_review = call_gemini(prompt)
    review, verdict = _extract_verdict(raw_review)

    result = {
        'repo_id': repo_id,
        'pr_number': pr_number,
        'title': pr['title'],
        'html_url': pr['html_url'],
        'author': pr['user']['login'],
        'head_sha': pr['head']['sha'],
        'files_changed': len(files),
        'additions': total_additions,
        'deletions': total_deletions,
        'files': [{
            'filename': f['filename'],
            'status': f['status'],
            'additions': f.get('additions', 0),
            'deletions': f.get('deletions', 0),
        } for f in files],
        'review': review,
        'verdict': verdict,
        'generated_at': datetime.datetime.utcnow().isoformat(),
        'status': 'completed',
    }

    return result, owner, repo_name
