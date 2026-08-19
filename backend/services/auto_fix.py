import difflib
import json
import time
from services.github_service import (
    get_repo_details, get_branch, create_branch, get_file_sha, update_file_content,
    create_pull_request,
)
from services.repo_reader import fetch_repo_tree_recursive
from services.gemini_service import call_gemini

MAX_CANDIDATE_FILES = 10
MAX_FIXES = 5

FIX_PROMPT_INSTRUCTIONS = """You are a careful, conservative code-fixing assistant. You will be shown several
source files from a repository. For each file, decide if it has a SAFE, MECHANICAL issue you can fix with
total confidence, from ONLY these categories:
- Hardcoded absolute local file paths (e.g. C:\\Users\\... or /home/...) that should be relative or config-driven
- Unsafe deserialization: pickle.load/pickle.loads used to load model/data files, which should use joblib instead
- Missing obvious type hints on function signatures (only add hints, never change logic)
- Clearly dead/duplicate imports

Do NOT do anything else: no refactors, no renames, no logic changes, no style-only reformatting, no
"improvements" beyond these categories. If a file has none of these issues, omit it entirely — never force a fix.

Respond with ONLY valid JSON (no markdown fences, no commentary), in exactly this shape:
{"fixes": [{"file": "path/exactly/as/given", "description": "one sentence: what changed and why", "new_content": "the FULL corrected file content"}]}
"""

def scan_for_fixes(github_token, repo_id, on_stage=None):
    """
    Scans a repo's files for safe, mechanical issues and returns candidate fixes with a
    diff preview. Nothing is written to GitHub here — this is read-only.
    """
    def stage(message):
        if on_stage:
            on_stage(message)

    stage('Fetching repository details...')
    repo = get_repo_details(github_token, repo_id)
    owner = repo['owner']['login']
    repo_name = repo['name']
    branch = repo.get('default_branch', 'main')

    stage('Walking the repository tree...')
    files = fetch_repo_tree_recursive(github_token, owner, repo_name, max_files=MAX_CANDIDATE_FILES, branch=branch)

    if not files:
        return {'repo_id': repo_id, 'branch': branch, 'fixes': []}

    stage(f'Scanning {len(files)} files for safe fixes...')
    prompt = FIX_PROMPT_INSTRUCTIONS + "\n\n=== FILES ===\n"
    for f in files:
        prompt += f"\n--- {f['path']} ---\n{f['content'][:6000]}\n"

    raw = call_gemini(prompt)
    candidate_fixes = _parse_fixes(raw)

    original_by_path = {f['path']: f['content'] for f in files}
    fixes = []
    for fix in candidate_fixes[:MAX_FIXES]:
        path = fix.get('file')
        new_content = fix.get('new_content')
        original = original_by_path.get(path)
        # Guard against hallucinated file paths or no-op / empty "fixes"
        if not path or not new_content or original is None or new_content.strip() == original.strip():
            continue
        diff = '\n'.join(difflib.unified_diff(
            original.splitlines(), new_content.splitlines(),
            fromfile=f'a/{path}', tofile=f'b/{path}', lineterm='',
        ))
        fixes.append({
            'file': path,
            'description': fix.get('description', ''),
            'diff': diff,
            'new_content': new_content,
        })

    return {'repo_id': repo_id, 'branch': branch, 'fixes': fixes}

def _parse_fixes(raw_text):
    text = raw_text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.startswith('json'):
            text = text[4:]
    try:
        data = json.loads(text)
        fixes = data.get('fixes', [])
        return fixes if isinstance(fixes, list) else []
    except Exception as e:
        print(f"Failed to parse fix-scan response: {e}")
        return []

def create_fix_pr(github_token, repo_id, base_branch, selected_fixes):
    """
    Creates a new branch off base_branch, commits each selected fix's new_content, and
    opens a PR back into base_branch. selected_fixes: [{file, description, new_content}].
    Raises ValueError on failure. Returns the created PR's API response dict.
    """
    if not selected_fixes:
        raise ValueError('No fixes selected')

    repo = get_repo_details(github_token, repo_id)
    owner = repo['owner']['login']
    repo_name = repo['name']

    base = get_branch(github_token, owner, repo_name, base_branch)
    if not base:
        raise ValueError(f'Could not read base branch "{base_branch}"')
    base_sha = base['commit']['sha']

    new_branch = f"gitcat/auto-fix-{int(time.time())}"
    if not create_branch(github_token, owner, repo_name, new_branch, base_sha):
        raise ValueError('Failed to create branch on GitHub')

    committed = []
    for fix in selected_fixes:
        path = fix['file']
        sha = get_file_sha(github_token, owner, repo_name, path, new_branch)
        if not sha:
            continue  # file no longer exists on this branch — skip rather than fail the whole PR
        ok = update_file_content(
            github_token, owner, repo_name, path, fix['new_content'],
            message=f"gitcat: {fix.get('description') or 'automated fix'}",
            branch=new_branch, sha=sha,
        )
        if ok:
            committed.append(fix)

    if not committed:
        raise ValueError('Failed to commit any of the selected fixes')

    body = "This PR was opened automatically by gitcat's auto-fix scan.\n\n" + "\n".join(
        f"- **{f['file']}**: {f.get('description') or 'automated fix'}" for f in committed
    ) + "\n\n*Review carefully before merging — this was generated by an AI, not a human.*"

    pr = create_pull_request(
        github_token, owner, repo_name,
        title=f"gitcat: automated fixes ({len(committed)} file{'s' if len(committed) != 1 else ''})",
        head=new_branch, base=base_branch, body=body,
    )
    if not pr:
        raise ValueError('Committed fixes but failed to open the pull request')

    return pr
