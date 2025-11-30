from flask import Blueprint, request, jsonify
from services.gemini_service import call_gemini
from services.github_service import (
    get_repo_details, get_repo_readme, get_repo_files, 
    get_file_content, get_repo_commits, get_repo_prs
)
from routes.auth import token_store
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
        
    # Build Comprehensive Context
    context = 'You are an expert AI coding assistant helping developers understand their GitHub repositories. You have deep knowledge of the codebase, recent activity, and pull requests.'
    
    if session.get('repoId'):
        try:
            repo = get_repo_details(github_token, session['repoId'])
            owner = repo['owner']['login']
            repo_name = repo['name']
            
            context += f"\n\n=== REPOSITORY CONTEXT ===\n"
            context += f"Name: {repo['name']}\n"
            context += f"Description: {repo.get('description', 'No description')}\n"
            context += f"Language: {repo['language']}\n"
            context += f"Stars: {repo['stargazers_count']}\n"
            context += f"Forks: {repo['forks_count']}\n"
            context += f"Open Issues: {repo['open_issues_count']}\n"
            
            # README
            readme = get_repo_readme(github_token, owner, repo_name)
            if readme:
                context += f"\n=== README (First 1500 chars) ===\n{readme[:1500]}\n"
            
            # Important Files
            files = get_repo_files(github_token, owner, repo_name)
            important_names = ['package.json', 'go.mod', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'Makefile', 'README.md']
            important_exts = ['.js', '.ts', '.py', '.go', '.rs', '.java', '.tsx', '.jsx']
            
            if files:
                important_files = []
                for f in files:
                    if f['type'] == 'file':
                        name = f['name']
                        if name in important_names or any(name.endswith(ext) for ext in important_exts):
                            content = get_file_content(github_token, owner, repo_name, f['path'])
                            if content:
                                important_files.append({'name': name, 'content': content[:2000]})
                                if len(important_files) >= 8:
                                    break
                
                if important_files:
                    context += f"\n=== IMPORTANT FILES ({len(important_files)}) ===\n"
                    for f in important_files:
                        context += f"\n--- {f['name']} (truncated) ---\n{f['content']}\n"
            
            # Recent Commits
            commits = get_repo_commits(github_token, owner, repo_name)
            if commits:
                context += "\n=== RECENT COMMITS ===\n"
                for c in commits:
                    msg = c['commit']['message'].split('\n')[0]
                    author = c['commit']['author']['name']
                    date = c['commit']['author']['date']
                    context += f"- {msg} (by {author}, {date})\n"
            
            # Recent Pull Requests
            prs = get_repo_prs(github_token, owner, repo_name)
            if prs:
                context += "\n=== RECENT PULL REQUESTS ===\n"
                for pr in prs:
                    context += f"- PR #{pr['number']}: {pr['title']}\n"
                    context += f"  State: {pr['state']}, Author: {pr['user']['login']}\n"
                    context += f"  Created: {pr['created_at']}, Updated: {pr['updated_at']}\n"
                    if pr.get('merged_at'):
                        context += f"  Merged: {pr['merged_at']}\n"
                    context += "\n"
                    
        except Exception as e:
            print(f"Chat Context Error: {e}")

    # History
    if session['messages']:
        context += '\n=== CONVERSATION HISTORY ===\n'
        for msg in session['messages'][-5:]:
            context += f"{msg['role']}: {msg['content']}\n"

    # Call AI
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
