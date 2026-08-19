from flask import Blueprint, request, jsonify
from services.gemini_service import call_gemini, call_gemini_with_tools
from services.github_service import (
    get_repo_details, get_repo_readme, get_repo_files,
    get_file_content, get_repo_commits, get_repo_prs
)
from routes.auth import token_store
from services.limiter import limiter
import datetime

chat_bp = Blueprint('chat', __name__)

# In-memory chat sessions
chat_sessions = {}

@chat_bp.route('/sessions', methods=['POST'])
def create_session():
    data = request.json
    session_id = int(datetime.datetime.now().timestamp() * 1000)
    
    chat_sessions[session_id] = {
        'userId': data.get('user_id'),
        'repoId': data.get('repo_id'),
        'title': data.get('title', 'New Chat'),
        'messages': [],
        'createdAt': datetime.datetime.utcnow().isoformat()
    }
    
    return jsonify({'session_id': session_id}), 201

@chat_bp.route('/sessions/<int:session_id>/messages')
def get_messages(session_id):
    session = chat_sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session['messages'])

@chat_bp.route('/message', methods=['POST'])
@limiter.limit("30 per hour")
def send_message():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)
    
    if not github_token:
        return jsonify({'error': 'Invalid token'}), 401

    data = request.json
    session_id = data.get('session_id')
    message = data.get('message')
    
    session = chat_sessions.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
        
    # Lightweight context: just repo metadata, no eager fetching of README/files/commits/PRs.
    context = (
        'You are an expert AI coding assistant helping developers understand their GitHub repositories. '
        'You have tools to look up the README, list and read files, and view recent commits and pull '
        'requests. Only call a tool when the question actually requires that information.'
    )

    owner = repo_name = None
    if session.get('repoId'):
        try:
            repo = get_repo_details(github_token, session['repoId'])
            owner = repo['owner']['login']
            repo_name = repo['name']

            context += f"\n\n=== REPOSITORY ===\n"
            context += f"Name: {repo['name']}\n"
            context += f"Description: {repo.get('description', 'No description')}\n"
            context += f"Language: {repo['language']}\n"
            context += f"Stars: {repo['stargazers_count']}\n"
            context += f"Forks: {repo['forks_count']}\n"
            context += f"Open Issues: {repo['open_issues_count']}\n"
        except Exception as e:
            print(f"Chat Context Error: {e}")

    # History
    if session['messages']:
        context += '\n=== CONVERSATION HISTORY ===\n'
        for msg in session['messages'][-5:]:
            context += f"{msg['role']}: {msg['content']}\n"

    # Tools the model can call on-demand instead of everything being prefetched.
    tools = []
    if owner and repo_name:
        def get_readme() -> str:
            """Get the repository's README file content."""
            readme = get_repo_readme(github_token, owner, repo_name)
            return readme[:4000] if readme else "No README found."

        def list_files(path: str = "") -> str:
            """List files and folders in the repository at the given path. Use an empty path for the repository root."""
            files = get_repo_files(github_token, owner, repo_name, path)
            if not files:
                return f"No files found at path '{path}'."
            return "\n".join(f"{f['type']}: {f['path']}" for f in files)

        def read_file(path: str) -> str:
            """Get the content of a specific file in the repository, given its path."""
            content = get_file_content(github_token, owner, repo_name, path)
            return content[:4000] if content else f"Could not read file: {path}"

        def get_recent_commits() -> str:
            """Get the 5 most recent commits to the repository."""
            commits = get_repo_commits(github_token, owner, repo_name)
            if not commits:
                return "No commits found."
            return "\n".join(
                f"- {c['commit']['message'].splitlines()[0]} (by {c['commit']['author']['name']}, {c['commit']['author']['date']})"
                for c in commits
            )

        def get_pull_requests() -> str:
            """Get the 5 most recent pull requests for the repository."""
            prs = get_repo_prs(github_token, owner, repo_name)
            if not prs:
                return "No pull requests found."
            return "\n".join(
                f"- PR #{pr['number']}: {pr['title']} (state: {pr['state']}, author: {pr['user']['login']})"
                for pr in prs
            )

        tools = [get_readme, list_files, read_file, get_recent_commits, get_pull_requests]

    # Call AI
    if tools:
        ai_response = call_gemini_with_tools(message, tools, context)
    else:
        ai_response = call_gemini(message, context)
    
    # Store messages
    session['messages'].append({
        'role': 'user',
        'content': message,
        'created_at': datetime.datetime.utcnow().isoformat()
    })
    session['messages'].append({
        'role': 'assistant',
        'content': ai_response,
        'created_at': datetime.datetime.utcnow().isoformat()
    })
    
    return jsonify({'response': ai_response})
