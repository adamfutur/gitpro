from flask import Blueprint, request, jsonify
from services.github_service import (
    get_user_repos,
    get_repo_details,
    get_repo_readme,
    get_repo_commits,
    get_repo_prs,
)
from services.repo_reader import fetch_repo_tree_recursive
from services.gemini_service import call_gemini
from services.cache import analysis_cache
from services.nlp_analyzer import analyze_code_file, generate_nlp_summary
from routes.auth import token_store
from services.db_service import save_analysis
import datetime
import jwt
from utils.jwt_utils import JWT_SECRET

repos_bp = Blueprint('repos', __name__)

@repos_bp.route('')
def list_repos():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401
    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)
    if not github_token:
        return jsonify({'error': 'Invalid token'}), 401
    try:
        repos = get_user_repos(github_token)
        transformed_repos = []
        for repo in repos:
            transformed_repos.append({
                'id': repo['id'],
                'name': repo['name'],
                'full_name': repo['full_name'],
                'description': repo['description'],
                'language': repo['language'],
                'stars_count': repo['stargazers_count'],
                'forks_count': repo['forks_count'],
                'open_issues_count': repo['open_issues_count'],
                'default_branch': repo['default_branch'],
                'private': repo['private'],
                'html_url': repo['html_url'],
                'created_at': repo['created_at'],
                'updated_at': repo['updated_at'],
                'analysis_status': 'pending'
            })
        return jsonify(transformed_repos)
    except Exception as e:
        print(f"Repo List Error: {e}")
        return jsonify({'error': 'Failed to fetch repositories'}), 500

@repos_bp.route('/<int:repo_id>')
def get_repo(repo_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401
    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)
    if not github_token:
        return jsonify({'error': 'Invalid token'}), 401
    try:
        repo = get_repo_details(github_token, repo_id)
        repo_data = {
            'id': repo['id'],
            'name': repo['name'],
            'full_name': repo['full_name'],
            'description': repo['description'],
            'language': repo['language'],
            'stars_count': repo['stargazers_count'],
            'forks_count': repo['forks_count'],
            'open_issues_count': repo['open_issues_count'],
            'default_branch': repo['default_branch'],
            'private': repo['private'],
            'html_url': repo['html_url'],
            'created_at': repo['created_at'],
            'updated_at': repo['updated_at'],
            'analysis_status': 'pending'
        }
        return jsonify(repo_data)
    except Exception as e:
        print(f"Repo Details Error: {e}")
        return jsonify({'error': 'Failed to fetch repository details'}), 500

@repos_bp.route('/<int:repo_id>/analyze', methods=['POST'])
def analyze_repo(repo_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401
    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)
    if not github_token:
        return jsonify({'error': 'Invalid token'}), 401
    # Decode JWT to obtain GitHub user ID
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        github_user_id = decoded['userId']
    except Exception:
        return jsonify({'error': 'Invalid token'}), 401
    try:
        repo = get_repo_details(github_token, repo_id)
        owner = repo['owner']['login']
        repo_name = repo['name']
        
        # Build comprehensive analysis prompt
        analysis_prompt = f"""Analyze this GitHub repository comprehensively:

Repository: {repo['name']}
Description: {repo.get('description', 'No description')}
Language: {repo['language']}
Stars: {repo.get('stargazers_count', 0)}
Forks: {repo.get('forks_count', 0)}
"""
        
        # README
        readme = get_repo_readme(github_token, owner, repo_name)
        if readme:
            analysis_prompt += f"\nREADME:\n{readme[:3000]}\n"
        
        # COMPREHENSIVE: Fetch 25 files with 6KB content each
        print(f"Fetching comprehensive repository tree for {owner}/{repo_name}...")
        important_files = fetch_repo_tree_recursive(github_token, owner, repo_name, max_files=25)
        nlp_analyses = []
        
        if important_files:
            analysis_prompt += f"\n\n=== CODE FILES ({len(important_files)} files analyzed) ===\n"
            for file_data in important_files:
                # Include more content per file for comprehensive understanding
                analysis_prompt += f"\n--- {file_data['path']} ---\n{file_data['content'][:4000]}\n"
                # COMPREHENSIVE: Disable fast_mode for full semantic analysis
                nlp_result = analyze_code_file(file_data['name'], file_data['content'], fast_mode=False)
                nlp_analyses.append(nlp_result)
        
        # COMPREHENSIVE: Include full NLP summary
        if nlp_analyses:
            nlp_summary = generate_nlp_summary(nlp_analyses)
            analysis_prompt += f"\n\n=== DETAILED NLP CODE ANALYSIS ===\n{nlp_summary}\n"
        
        # Commits & PRs
        commits = get_repo_commits(github_token, owner, repo_name)
        if commits:
            analysis_prompt += "\n\nRecent Commits:\n"
            for c in commits[:10]:  # Include more commits
                msg = c['commit']['message'].split('\n')[0]
                author = c['commit']['author']['name']
                date = c['commit']['author']['date']
                analysis_prompt += f"- {msg} (by {author}, {date})\n"
        
        prs = get_repo_prs(github_token, owner, repo_name)
        if prs:
            analysis_prompt += "\n\nRecent Pull Requests:\n"
            for pr in prs[:10]:  # Include more PRs
                analysis_prompt += f"- PR #{pr['number']}: {pr['title']} (State: {pr['state']})\n"
        
        # COMPREHENSIVE: Request detailed analysis from AI
        analysis_prompt += """

Based on the comprehensive analysis above, provide a detailed evaluation including:
1. Code Quality Assessment (score 1-10 with detailed justification)
2. Architecture Overview (patterns, structure, design decisions)
3. Security Considerations (vulnerabilities, best practices)
4. Performance Insights (bottlenecks, optimization opportunities)
5. Maintainability Assessment (technical debt, documentation quality)
6. Suggested Improvements (prioritized list addressing code smells)
7. Technology Stack Analysis (dependencies, versions, compatibility)
8. Team Collaboration Indicators (commit patterns, PR quality)
"""
        
        # Call Gemini AI
        print("Calling Gemini AI for comprehensive analysis...")
        analysis_result = call_gemini(analysis_prompt)
        
        # Anomaly detection
        print("Running ML anomaly detection...")
        from services.anomaly_detector import detect_code_anomalies
        anomalies = detect_code_anomalies(nlp_analyses)
        
        # KPI calculation
        print("Calculating repository KPIs...")
        from services.kpi_calculator import calculate_kpis
        kpis = calculate_kpis(nlp_analyses, repo, commits, prs)
        
        result = {
            'repo_id': repo_id,
            'repo_name': repo['name'],
            'repo_full_name': repo['full_name'],
            'analysis': analysis_result,
            'kpis': kpis,
            'anomalies': anomalies,
            'generated_at': datetime.datetime.utcnow().isoformat(),
            'status': 'completed'
        }
        
        # Persist to database
        save_analysis(repo_id, github_user_id, result)
        # Cache for backward compatibility
        analysis_cache[repo_id] = result
        
        return jsonify(result)
    except Exception as e:
        print(f"Analysis Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to analyze repository'}), 500

@repos_bp.route('/analysis/<int:repo_id>')
def get_analysis_result(repo_id):
    if repo_id in analysis_cache:
        return jsonify(analysis_cache[repo_id])
    return jsonify({'status': 'not_analyzed', 'message': 'No analysis available'}), 404
