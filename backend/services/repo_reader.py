import requests
import os

GITHUB_API_URL = "https://api.github.com"

def fetch_repo_tree_recursive(token, owner, repo, max_files=25):
    """
    Recursively fetch repository files and their content.
    Returns a list of {path, name, content} dictionaries.
    """
    headers = {'Authorization': f'token {token}'}
    files_with_content = []
    
    # Important file patterns
    important_names = ['package.json', 'go.mod', 'requirements.txt', 'Dockerfile', 'docker-compose.yml', 'Makefile', 'README.md']
    important_exts = ['.js', '.ts', '.py', '.go', '.rs', '.java', '.tsx', '.jsx', '.cpp', '.c', '.cs', '.rb', '.php']
    
    def is_important_file(filename):
        return filename in important_names or any(filename.endswith(ext) for ext in important_exts)
    
    def fetch_directory(path=''):
        """Recursively fetch files from a directory."""
        if len(files_with_content) >= max_files:
            return
        
        try:
            url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{path}"
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                return
            
            items = response.json()
            
            for item in items:
                if len(files_with_content) >= max_files:
                    break
                
                if item['type'] == 'file' and is_important_file(item['name']):
                    # Fetch file content
                    try:
                        file_response = requests.get(item['url'], headers=headers)
                        if file_response.status_code == 200:
                            file_data = file_response.json()
                            if file_data.get('content'):
                                import base64
                                content = base64.b64decode(file_data['content']).decode('utf-8', errors='ignore')
                                files_with_content.append({
                                    'path': item['path'],
                                    'name': item['name'],
                                    'content': content[:6000]  # Comprehensive mode: more content
                                })
                    except Exception as e:
                        print(f"Error fetching {item['path']}: {e}")
                
                elif item['type'] == 'dir':
                    # Recursively fetch subdirectory
                    # Skip common directories that are usually not important
                    skip_dirs = ['node_modules', 'vendor', 'dist', 'build', '.git', '__pycache__', 'venv', 'env']
                    if item['name'] not in skip_dirs:
                        fetch_directory(item['path'])
        
        except Exception as e:
            print(f"Error fetching directory {path}: {e}")
    
    # Start from root
    fetch_directory()
    
    return files_with_content
