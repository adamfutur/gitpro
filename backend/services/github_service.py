import base64
import requests
import os

GITHUB_API_URL = "https://api.github.com"
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')

def exchange_code_for_token(code):
    url = "https://github.com/login/oauth/access_token"
    payload = {
        'client_id': GITHUB_CLIENT_ID,
        'client_secret': GITHUB_CLIENT_SECRET,
        'code': code
    }
    headers = {'Accept': 'application/json'}
    response = requests.post(url, json=payload, headers=headers)
    return response.json().get('access_token')

def get_github_user(token):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/user", headers=headers)
    return response.json()

def get_user_repos(token):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/user/repos?sort=updated&per_page=30", headers=headers)
    return response.json()

def get_repo_details(token, repo_id):
    headers = {'Authorization': f'token {token}'}
    # First get all repos to find the one with matching ID (inefficient but matches previous logic)
    # Better: fetch directly if we had owner/name, but we only have ID.
    # GitHub API allows fetching by ID: /repositories/:id
    response = requests.get(f"{GITHUB_API_URL}/repositories/{repo_id}", headers=headers)
    return response.json()

def get_repo_readme(token, owner, repo):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/readme", headers=headers)
    if response.status_code == 200:
        content = response.json().get('content', '')
        return base64.b64decode(content).decode('utf-8')
    return None

def get_repo_files(token, owner, repo, path=''):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_file_content(token, owner, repo, path):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}", headers=headers)
    if response.status_code == 200:
        content = response.json().get('content', '')
        return base64.b64decode(content).decode('utf-8')
    return None

def get_repo_commits(token, owner, repo):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits?per_page=5", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_repo_prs(token, owner, repo):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls?state=all&per_page=5", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def list_pull_requests(token, owner, repo, state='open', per_page=30):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
        headers=headers,
        params={'state': state, 'per_page': per_page, 'sort': 'created', 'direction': 'desc'},
    )
    if response.status_code == 200:
        return response.json()
    return []

def get_pr_details(token, owner, repo, pr_number):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def get_pr_files(token, owner, repo, pr_number, per_page=100):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files",
        headers=headers,
        params={'per_page': per_page},
    )
    if response.status_code == 200:
        return response.json()
    return []

def post_pr_comment(token, owner, repo, pr_number, body):
    """Posts a comment on a pull request (PRs are issues under the hood on GitHub)."""
    headers = {'Authorization': f'token {token}'}
    response = requests.post(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers=headers,
        json={'body': body},
    )
    if response.status_code == 201:
        return response.json()
    return None

def create_webhook(token, owner, repo, webhook_url, secret, events=('pull_request',)):
    """Registers a webhook on the repo. Returns the created hook's id, or None on failure."""
    headers = {'Authorization': f'token {token}'}
    response = requests.post(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/hooks",
        headers=headers,
        json={
            'name': 'web',
            'active': True,
            'events': list(events),
            'config': {
                'url': webhook_url,
                'content_type': 'json',
                'secret': secret,
            },
        },
    )
    if response.status_code == 201:
        return response.json().get('id')
    return None

def delete_webhook(token, owner, repo, webhook_id):
    headers = {'Authorization': f'token {token}'}
    response = requests.delete(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/hooks/{webhook_id}",
        headers=headers,
    )
    return response.status_code == 204

def get_branch(token, owner, repo, branch):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(f"{GITHUB_API_URL}/repos/{owner}/{repo}/branches/{branch}", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def create_branch(token, owner, repo, new_branch, from_sha):
    """Creates a new branch (git ref) pointing at from_sha. Returns True on success."""
    headers = {'Authorization': f'token {token}'}
    response = requests.post(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/refs",
        headers=headers,
        json={'ref': f'refs/heads/{new_branch}', 'sha': from_sha},
    )
    return response.status_code == 201

def get_file_sha(token, owner, repo, path, branch):
    """Returns the current blob sha for a file on a branch, or None if it doesn't exist there."""
    headers = {'Authorization': f'token {token}'}
    response = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
        headers=headers,
        params={'ref': branch},
    )
    if response.status_code == 200:
        return response.json().get('sha')
    return None

def update_file_content(token, owner, repo, path, new_content, message, branch, sha):
    """Commits new_content to path on branch. sha must be the file's current blob sha (from get_file_sha)."""
    headers = {'Authorization': f'token {token}'}
    payload = {
        'message': message,
        'content': base64.b64encode(new_content.encode('utf-8')).decode('utf-8'),
        'branch': branch,
        'sha': sha,
    }
    response = requests.put(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}",
        headers=headers,
        json=payload,
    )
    return response.status_code in (200, 201)

def create_commit_status(token, owner, repo, sha, state, description, context, target_url=None):
    """
    Sets a commit status (state: 'pending' | 'success' | 'failure' | 'error') — the classic
    Status API, usable by OAuth App tokens. Shows up in the PR merge box and can be required
    via GitHub branch protection's "Require status checks to pass".
    """
    headers = {'Authorization': f'token {token}'}
    payload = {
        'state': state,
        'description': description[:140],  # GitHub caps this field
        'context': context,
    }
    if target_url:
        payload['target_url'] = target_url
    response = requests.post(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/statuses/{sha}",
        headers=headers,
        json=payload,
    )
    return response.status_code == 201

def create_pull_request(token, owner, repo, title, head, base, body):
    headers = {'Authorization': f'token {token}'}
    response = requests.post(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls",
        headers=headers,
        json={'title': title, 'head': head, 'base': base, 'body': body},
    )
    if response.status_code == 201:
        return response.json()
    return None
