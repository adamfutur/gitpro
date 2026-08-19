from flask import Blueprint, request, jsonify
from services.db_service import enable_share, disable_share, get_share, get_analysis
from routes.auth import token_store
import jwt
from utils.jwt_utils import JWT_SECRET

share_bp = Blueprint('share', __name__)
public_bp = Blueprint('public', __name__)

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

@share_bp.route('/<int:repo_id>/share', methods=['GET'])
def get_share_status(repo_id):
    github_token, _ = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401
    config = get_share(repo_id)
    return jsonify({'enabled': config is not None})

@share_bp.route('/<int:repo_id>/share', methods=['POST'])
def enable_share_route(repo_id):
    github_token, github_user_id = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401

    if not get_analysis(repo_id, github_user_id):
        return jsonify({'error': 'Run an analysis on this repo before sharing it'}), 400

    enable_share(repo_id, github_user_id)
    return jsonify({'enabled': True})

@share_bp.route('/<int:repo_id>/share', methods=['DELETE'])
def disable_share_route(repo_id):
    github_token, _ = _authenticated_user()
    if not github_token:
        return jsonify({'error': 'Unauthorized'}), 401
    disable_share(repo_id)
    return jsonify({'enabled': False})

@public_bp.route('/repos/<int:repo_id>/card')
def get_public_card(repo_id):
    """No authentication — this is the whole point. Only returns data the owner explicitly
    opted to make public via the /share toggle, and only what's needed for the card."""
    config = get_share(repo_id)
    if not config:
        return jsonify({'error': 'not_shared'}), 404

    analysis = get_analysis(repo_id, config['github_user_id'])
    if not analysis:
        return jsonify({'error': 'not_shared'}), 404

    kpis = analysis.get('kpis') or {}
    summary = kpis.get('summary') or {}

    return jsonify({
        'repo_name': analysis.get('repo_name'),
        'repo_full_name': analysis.get('repo_full_name'),
        'grade': summary.get('grade'),
        'overall_health_score': summary.get('overall_health_score'),
        'analyzed_files': summary.get('analyzed_files'),
        'quality_score': (kpis.get('quality') or {}).get('quality_score'),
        'maintainability_index': (kpis.get('maintainability') or {}).get('maintainability_index'),
        'productivity_score': (kpis.get('productivity') or {}).get('productivity_score'),
        'security_risk_score': (kpis.get('security') or {}).get('risk_score'),
        'generated_at': analysis.get('generated_at'),
    })
