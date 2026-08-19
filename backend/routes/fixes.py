from flask import Blueprint, request, jsonify
from services.auto_fix import scan_for_fixes, create_fix_pr
from services.cache import fix_scan_jobs
from services.limiter import limiter
from routes.auth import token_store
import datetime
import jwt
import threading
import uuid
from utils.jwt_utils import JWT_SECRET

fixes_bp = Blueprint('fixes', __name__)

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

def _run_fix_scan(job_id, repo_id, github_token):
    def set_stage(message):
        fix_scan_jobs[job_id]['stage'] = message

    try:
        fix_scan_jobs[job_id]['status'] = 'running'
        result = scan_for_fixes(github_token, repo_id, on_stage=set_stage)
        fix_scan_jobs[job_id]['status'] = 'completed'
        fix_scan_jobs[job_id]['result'] = result
        fix_scan_jobs[job_id]['finished_at'] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        print(f"Fix Scan Error: {e}")
        import traceback
        traceback.print_exc()
        fix_scan_jobs[job_id]['status'] = 'failed'
        fix_scan_jobs[job_id]['error'] = 'Failed to scan for fixes'
        fix_scan_jobs[job_id]['finished_at'] = datetime.datetime.utcnow().isoformat()

@fixes_bp.route('/<int:repo_id>/fixes/scan', methods=['POST'])
@limiter.limit("10 per hour")
def start_fix_scan(repo_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    job_id = uuid.uuid4().hex
    fix_scan_jobs[job_id] = {
        'job_id': job_id,
        'repo_id': repo_id,
        'github_user_id': github_user_id,
        'status': 'pending',
        'stage': 'Queued...',
        'result': None,
        'error': None,
        'started_at': datetime.datetime.utcnow().isoformat(),
        'finished_at': None,
    }

    thread = threading.Thread(target=_run_fix_scan, args=(job_id, repo_id, github_token), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'pending'}), 202

@fixes_bp.route('/<int:repo_id>/fixes/scan/jobs/<job_id>')
def get_fix_scan_job(repo_id, job_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    job = fix_scan_jobs.get(job_id)
    if not job or job['repo_id'] != repo_id or job['github_user_id'] != github_user_id:
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

@fixes_bp.route('/<int:repo_id>/fixes/apply', methods=['POST'])
@limiter.limit("10 per hour")
def apply_fixes(repo_id):
    """Actually writes to GitHub: creates a branch, commits the selected fixes, opens a PR."""
    github_token, _github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json or {}
    branch = data.get('branch')
    selected_fixes = data.get('fixes')
    if not branch or not selected_fixes:
        return jsonify({'error': 'branch and fixes are required'}), 400

    try:
        pr = create_fix_pr(github_token, repo_id, branch, selected_fixes)
        return jsonify({
            'number': pr['number'],
            'html_url': pr['html_url'],
            'title': pr['title'],
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Apply Fixes Error: {e}")
        return jsonify({'error': 'Failed to create fix PR'}), 500
