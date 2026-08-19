import datetime
import re
from services.github_service import get_repo_details
from services.repo_reader import fetch_repo_tree_recursive
from services.gemini_service import call_gemini

MAX_FILES = 12

DIAGRAM_BLOCK_RE = re.compile(r"```mermaid\s*(.*?)```", re.DOTALL)

def generate_architecture_diagram(github_token, repo_id, on_stage=None):
    """Generates a high-level Mermaid flowchart of a repo's architecture from its key files."""
    def stage(message):
        if on_stage:
            on_stage(message)

    stage('Fetching repository details...')
    repo = get_repo_details(github_token, repo_id)
    owner = repo['owner']['login']
    repo_name = repo['name']
    branch = repo.get('default_branch', 'main')

    stage('Walking the repository tree...')
    files = fetch_repo_tree_recursive(github_token, owner, repo_name, max_files=MAX_FILES, branch=branch)

    stage('Generating architecture diagram with Gemini...')
    prompt = f"""You are a software architect. Based on the files below from the repository
"{repo['full_name']}", produce a high-level architecture diagram as a Mermaid flowchart.

Rules:
- Output ONLY a single ```mermaid code fence, nothing else — no commentary before or after it.
- Start with "flowchart TD".
- Keep node labels short (2-5 words), plain text only — no parentheses, quotes, or special characters.
- Show the main components/modules and how they connect (data flow, calls, dependencies) —
  not a list of every file. Group related files into one logical component when it makes sense.
- Aim for 6-14 nodes.

=== FILES ===
"""
    for f in files:
        prompt += f"\n--- {f['path']} ---\n{f['content'][:3000]}\n"

    raw = call_gemini(prompt)
    diagram = _extract_diagram(raw)

    return {
        'repo_id': repo_id,
        'repo_full_name': repo['full_name'],
        'diagram': diagram,
        'generated_at': datetime.datetime.utcnow().isoformat(),
    }

def _extract_diagram(raw_text):
    match = DIAGRAM_BLOCK_RE.search(raw_text)
    if match:
        return match.group(1).strip()
    # Gemini occasionally forgets the fence — accept a bare flowchart/graph body too
    stripped = raw_text.strip()
    if stripped.startswith(('flowchart', 'graph')):
        return stripped
    return ''
