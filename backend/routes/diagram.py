from flask import Blueprint, request, jsonify
from services.architecture import generate_architecture_diagram
from services.cache import diagram_jobs
from services.limiter import limiter
from routes.auth import token_store
import datetime
import jwt
import threading
import uuid
from utils.jwt_utils import JWT_SECRET

diagram_bp = Blueprint('diagram', __name__)

def _authenticated_user():
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

def _run_diagram_scan(job_id, repo_id, github_token):
    def set_stage(message):
        diagram_jobs[job_id]['stage'] = message

    try:
        diagram_jobs[job_id]['status'] = 'running'
        result = generate_architecture_diagram(github_token, repo_id, on_stage=set_stage)
        diagram_jobs[job_id]['status'] = 'completed'
        diagram_jobs[job_id]['result'] = result
        diagram_jobs[job_id]['finished_at'] = datetime.datetime.utcnow().isoformat()
    except Exception as e:
        print(f"Diagram Error: {e}")
        import traceback
        traceback.print_exc()
        diagram_jobs[job_id]['status'] = 'failed'
        diagram_jobs[job_id]['error'] = 'Failed to generate diagram'
        diagram_jobs[job_id]['finished_at'] = datetime.datetime.utcnow().isoformat()

@diagram_bp.route('/<int:repo_id>/diagram', methods=['POST'])
@limiter.limit("10 per hour")
def start_diagram(repo_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    job_id = uuid.uuid4().hex
    diagram_jobs[job_id] = {
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

    thread = threading.Thread(target=_run_diagram_scan, args=(job_id, repo_id, github_token), daemon=True)
    thread.start()

    return jsonify({'job_id': job_id, 'status': 'pending'}), 202

@diagram_bp.route('/<int:repo_id>/diagram/jobs/<job_id>')
def get_diagram_job(repo_id, job_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    job = diagram_jobs.get(job_id)
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
