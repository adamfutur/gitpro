import datetime
from services.github_service import get_repo_details, get_pr_details, get_pr_files
from services.gemini_service import call_gemini
from services.pr_risk import analyze_pr_risk
from services.change_impact import build_change_impact_graph
from services.review_verdict import extract_verdict as _extract_verdict
from services.repo_reader import fetch_repo_tree_recursive

MAX_REVIEWED_FILES = 20
MAX_PATCH_CHARS = 3000

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

    stage('Mapping change impact...')
    # Read a bounded sample at the PR head, not an unrelated default-branch snapshot.
    # GitHub may not expose fork commits through the base repository; graph then stays partial.
    try:
        sampled_files = fetch_repo_tree_recursive(
            github_token, owner, repo_name, max_files=80,
            branch=pr['head']['sha'],
            priority_paths=[f['filename'] for f in files],
        )
    except Exception:
        sampled_files = []
    impact_graph = build_change_impact_graph(files, sampled_files)

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
        'risk_radar': analyze_pr_risk(files, MAX_REVIEWED_FILES, MAX_PATCH_CHARS),
        'impact_graph': impact_graph,
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
