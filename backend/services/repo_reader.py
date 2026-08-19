import base64
from concurrent.futures import ThreadPoolExecutor
import requests

GITHUB_API_URL = "https://api.github.com"

IMPORTANT_NAMES = ['package.json', 'go.mod', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'Makefile', 'README.md']
IMPORTANT_EXTS = ['.js', '.ts', '.py', '.go', '.rs', '.java', '.tsx', '.jsx', '.cpp', '.c', '.cs', '.rb', '.php']
SKIP_DIRS = {'node_modules', 'vendor', 'dist', 'build', '.git', '__pycache__', 'venv', 'env'}


def _is_important_file(path):
    parts = path.split('/')
    if SKIP_DIRS.intersection(parts[:-1]):
        return False
    name = parts[-1]
    return name in IMPORTANT_NAMES or any(name.endswith(ext) for ext in IMPORTANT_EXTS)


def fetch_repo_tree_recursive(token, owner, repo, max_files=25, branch='main'):
    """
    Fetch up to `max_files` important source files from the repo.

    Discovers the whole file tree with a single Git Trees API call (instead of
    walking directories one API call at a time), then fetches the matching file
    contents concurrently. Returns a list of {path, name, content} dictionaries.
    """
    session = requests.Session()
    session.headers.update({'Authorization': f'token {token}'})

    try:
        tree_response = session.get(
            f"{GITHUB_API_URL}/repos/{owner}/{repo}/git/trees/{branch}",
            params={'recursive': '1'},
        )
        if tree_response.status_code != 200:
            return []
        tree = tree_response.json().get('tree', [])
    except Exception as e:
        print(f"Error fetching repo tree: {e}")
        return []

    candidates = [
        item for item in tree
        if item.get('type') == 'blob' and _is_important_file(item['path'])
    ][:max_files]

    def fetch_content(item):
        try:
            blob_response = session.get(item['url'])
            if blob_response.status_code != 200:
                return None
            blob = blob_response.json()
            if blob.get('encoding') != 'base64' or not blob.get('content'):
                return None
            content = base64.b64decode(blob['content']).decode('utf-8', errors='ignore')
            path = item['path']
            return {
                'path': path,
                'name': path.rsplit('/', 1)[-1],
                'content': content[:6000],  # Comprehensive mode: more content
            }
        except Exception as e:
            print(f"Error fetching {item['path']}: {e}")
            return None

    with ThreadPoolExecutor(max_workers=8) as executor:
        # map() preserves candidate order in its results, even though fetches run concurrently
        results = executor.map(fetch_content, candidates)

    return [r for r in results if r]
