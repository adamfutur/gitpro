from flask import Blueprint, request, jsonify
from services.cache import analysis_cache
from routes.auth import token_store
from services.db_service import get_analysis, get_analysis_history
from utils.jwt_utils import JWT_SECRET
import jwt

dashboard_bp = Blueprint('dashboard', __name__)

def _authenticated_user_id(token):
    """Decode the app JWT to get the GitHub user id, or None if invalid."""
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return decoded['userId']
    except Exception:
        return None

@dashboard_bp.route('/<int:repo_id>')
def get_dashboard(repo_id):
    """Get comprehensive dashboard data for a repository."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)

    if not github_token:
        return jsonify({'error': 'Invalid token'}), 401

    github_user_id = _authenticated_user_id(token)
    if github_user_id is None:
        return jsonify({'error': 'Invalid token'}), 401

    # Try cache first (scoped to this user), then fall back to the database
    analysis = analysis_cache.get((repo_id, github_user_id))
    if not analysis:
        analysis = get_analysis(repo_id, github_user_id)

    if not analysis:
        return jsonify({
            'error': 'No analysis available',
            'message': 'Please run analysis first'
        }), 404
    
    # Extract dashboard data
    dashboard_data = {
        'repo_id': repo_id,
        'kpis': analysis.get('kpis', {}),
        'anomalies': analysis.get('anomalies', []),
        'generated_at': analysis.get('generated_at'),
        'status': analysis.get('status')
    }
    
    return jsonify(dashboard_data)

@dashboard_bp.route('/<int:repo_id>/kpis')
def get_kpis(repo_id):
    """Get only KPIs for a repository."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)

    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    github_user_id = _authenticated_user_id(token)
    if github_user_id is None:
        return jsonify({'error': 'Unauthorized'}), 401

    analysis = analysis_cache.get((repo_id, github_user_id))
    if not analysis:
        analysis = get_analysis(repo_id, github_user_id)

    if not analysis or 'kpis' not in analysis:
        return jsonify({'error': 'No KPIs available'}), 404
    
    return jsonify(analysis['kpis'])

@dashboard_bp.route('/<int:repo_id>/anomalies')
def get_anomalies(repo_id):
    """Get only anomalies for a repository."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)

    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    github_user_id = _authenticated_user_id(token)
    if github_user_id is None:
        return jsonify({'error': 'Unauthorized'}), 401

    analysis = analysis_cache.get((repo_id, github_user_id))
    if not analysis:
        analysis = get_analysis(repo_id, github_user_id)

    if not analysis or 'anomalies' not in analysis:
        return jsonify({'error': 'No anomalies available'}), 404
    
    return jsonify({
        'anomalies': analysis['anomalies'],
        'count': len(analysis['anomalies'])
    })

@dashboard_bp.route('/<int:repo_id>/history')
def get_history(repo_id):
    """Returns this repo's analysis runs over time (oldest first), for the trend chart."""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401

    token = auth_header.split(" ")[1]
    if not token_store.get(token):
        return jsonify({'error': 'Unauthorized'}), 401

    github_user_id = _authenticated_user_id(token)
    if github_user_id is None:
        return jsonify({'error': 'Unauthorized'}), 401

    history = get_analysis_history(repo_id, github_user_id)
    return jsonify({'repo_id': repo_id, 'history': history})
