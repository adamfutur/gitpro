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
        import base64
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
        import base64
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
