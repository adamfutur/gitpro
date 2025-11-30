from flask import Blueprint, request, jsonify
from services.cache import analysis_cache
from routes.auth import token_store
from services.db_service import get_analysis

dashboard_bp = Blueprint('dashboard', __name__)

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
    
    # Try cache first
    analysis = analysis_cache.get(repo_id)
    if not analysis:
        # Fallback to DB using user ID from token
        try:
            import jwt
            from utils.jwt_utils import JWT_SECRET
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            github_user_id = decoded['userId']
            analysis = get_analysis(repo_id, github_user_id)
        except Exception:
            analysis = None
    
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
    
    analysis = analysis_cache.get(repo_id)
    if not analysis:
        try:
            import jwt
            from utils.jwt_utils import JWT_SECRET
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            github_user_id = decoded['userId']
            analysis = get_analysis(repo_id, github_user_id)
        except Exception:
            analysis = None

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
    
    analysis = analysis_cache.get(repo_id)
    if not analysis:
        try:
            import jwt
            from utils.jwt_utils import JWT_SECRET
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            github_user_id = decoded['userId']
            analysis = get_analysis(repo_id, github_user_id)
        except Exception:
            analysis = None
    
    if not analysis or 'anomalies' not in analysis:
        return jsonify({'error': 'No anomalies available'}), 404
    
    return jsonify({
        'anomalies': analysis['anomalies'],
        'count': len(analysis['anomalies'])
    })
