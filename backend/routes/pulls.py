from flask import Blueprint, request, jsonify
from services.github_service import get_repo_details, list_pull_requests, create_webhook, delete_webhook
from services.pr_review import build_pr_review
from services.cache import pr_analysis_cache, pr_analysis_jobs
from services.db_service import enable_auto_review, disable_auto_review, get_auto_review
from services.limiter import limiter
from routes.auth import token_store
import datetime
import jwt
import os
import threading
import uuid
from utils.jwt_utils import JWT_SECRET

pulls_bp = Blueprint('pulls', __name__)

def _authenticated_user():
    """Returns (github_token, github_user_id), or (None, None) if unauthenticated/invalid."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None, None
    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)
    if not github_token:
        return None, None
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return github_token, decoded['userId']
    except Exception:
        return None, None

@pulls_bp.route('/<int:repo_id>/pulls')
def list_pulls(repo_id):
    github_token, _ = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        repo = get_repo_details(github_token, repo_id)
        owner = repo['owner']['login']
        repo_name = repo['name']
        prs = list_pull_requests(github_token, owner, repo_name, state='open')
        result = [{
            'number': pr['number'],
            'title': pr['title'],
            'state': pr['state'],
            'user': pr['user']['login'],
            'created_at': pr['created_at'],
            'updated_at': pr['updated_at'],
            'html_url': pr['html_url'],
            'draft': pr.get('draft', False),
        } for pr in prs]
        return jsonify(result)
    except Exception as e:
        print(f"List PRs Error: {e}")
        return jsonify({'error': 'Failed to fetch pull requests'}), 500

def _run_pr_analysis(job_id, repo_id, pr_number, github_user_id, github_token):
    """Runs build_pr_review in a background thread, tracking progress on pr_analysis_jobs[job_id]."""
    def set_stage(message):
        pr_analysis_jobs[job_id]['stage'] = message

    try:
        pr_analysis_jobs[job_id]['status'] = 'running'
        result, _owner, _repo_name = build_pr_review(github_token, repo_id, pr_number, on_stage=set_stage)

        pr_analysis_cache[(repo_id, pr_number, github_user_id)] = result
        pr_analysis_jobs[job_id]['status'] = 'completed'
        pr_analysis_jobs[job_id]['result'] = result
        pr_analysis_jobs[job_id]['finished_at'] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        print(f"PR Analysis Error: {e}")
        import traceback
        traceback.print_exc()
        pr_analysis_jobs[job_id]['status'] = 'failed'
        pr_analysis_jobs[job_id]['error'] = 'Failed to analyze pull request'
        pr_analysis_jobs[job_id]['finished_at'] = datetime.datetime.utcnow().isoformat()

@pulls_bp.route('/<int:repo_id>/pulls/<int:pr_number>/analyze', methods=['POST'])
@limiter.limit("10 per hour")
def analyze_pr(repo_id, pr_number):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    job_id = uuid.uuid4().hex
    pr_analysis_jobs[job_id] = {
        'job_id': job_id,
        'repo_id': repo_id,
        'pr_number': pr_number,
        'github_user_id': github_user_id,
        'status': 'pending',
        'stage': 'Queued...',
        'result': None,
        'error': None,
        'started_at': datetime.datetime.utcnow().isoformat(),
        'finished_at': None,
    }

    thread = threading.Thread(
        target=_run_pr_analysis,
        args=(job_id, repo_id, pr_number, github_user_id, github_token),
        daemon=True,
    )
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'pending'}), 202

@pulls_bp.route('/<int:repo_id>/pulls/<int:pr_number>/analyze/jobs/<job_id>')
def get_pr_analysis_job(repo_id, pr_number, job_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    job = pr_analysis_jobs.get(job_id)
    if not job or job['repo_id'] != repo_id or job['pr_number'] != pr_number or job['github_user_id'] != github_user_id:
        return jsonify({'error': 'Job not found'}), 404

    response = {
        'job_id': job['job_id'],
        'status': job['status'],
        'stage': job['stage'],
        'started_at': job['started_at'],
        'finished_at': job['finished_at'],
    }
    if job['status'] == 'completed':
        response['result'] = job['result']
    elif job['status'] == 'failed':
        response['error'] = job['error']
    return jsonify(response)

@pulls_bp.route('/<int:repo_id>/pulls/<int:pr_number>/analysis')
def get_pr_analysis(repo_id, pr_number):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    cache_key = (repo_id, pr_number, github_user_id)
    if cache_key in pr_analysis_cache:
        return jsonify(pr_analysis_cache[cache_key])
    return jsonify({'status': 'not_analyzed', 'message': 'No analysis available'}), 404

@pulls_bp.route('/<int:repo_id>/auto-review', methods=['GET'])
def get_auto_review_status(repo_id):
    github_token, _ = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401
    config = get_auto_review(repo_id)
    return jsonify({'enabled': config is not None})

@pulls_bp.route('/<int:repo_id>/auto-review', methods=['POST'])
def enable_auto_review_route(repo_id):
    """Registers a GitHub webhook so every new/updated PR on this repo gets an
    automatic AI review posted as a comment, without anyone visiting gitcat."""
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    backend_url = os.getenv('BACKEND_PUBLIC_URL', '').rstrip('/')
    webhook_secret = os.getenv('GITHUB_WEBHOOK_SECRET')
    if not backend_url or not webhook_secret:
        return jsonify({
            'error': 'Auto-review is not configured on the server '
                     '(BACKEND_PUBLIC_URL / GITHUB_WEBHOOK_SECRET missing).'
        }), 500

    try:
        repo = get_repo_details(github_token, repo_id)
        owner = repo['owner']['login']
        repo_name = repo['name']

        webhook_id = create_webhook(
            github_token, owner, repo_name,
            webhook_url=f"{backend_url}/api/webhooks/github",
            secret=webhook_secret,
        )
        if not webhook_id:
            return jsonify({'error': 'Failed to create webhook on GitHub. You may need admin access to this repo.'}), 400

        enable_auto_review(repo_id, github_user_id, repo['full_name'], github_token, webhook_id)
        return jsonify({'enabled': True})
    except Exception as e:
        print(f"Enable Auto-Review Error: {e}")
        return jsonify({'error': 'Failed to enable auto-review'}), 500

@pulls_bp.route('/<int:repo_id>/auto-review', methods=['DELETE'])
def disable_auto_review_route(repo_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    config = get_auto_review(repo_id)
    if not config:
        return jsonify({'enabled': False})

    try:
        repo = get_repo_details(github_token, repo_id)
        owner = repo['owner']['login']
        repo_name = repo['name']
        if config.get('webhook_id'):
            delete_webhook(github_token, owner, repo_name, config['webhook_id'])
    except Exception as e:
        print(f"Disable Auto-Review Warning: {e}")
        # Still remove the local record even if the GitHub-side cleanup failed
        # (e.g. the webhook was already deleted manually).

    disable_auto_review(repo_id)
    return jsonify({'enabled': False})
