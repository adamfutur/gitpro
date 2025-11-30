from flask import Blueprint, request, jsonify
from services.github_service import (
    get_repo_details, get_repo_readme, get_repo_files, 
    get_file_content, get_repo_commits, get_repo_prs
)
from services.gemini_service import call_gemini
from routes.auth import token_store
import datetime

analysis_bp = Blueprint('analysis', __name__)

from services.cache import analysis_cache

@analysis_bp.route('/<int:repo_id>')
def get_analysis(repo_id):
    if repo_id in analysis_cache:
        return jsonify(analysis_cache[repo_id])
    
    return jsonify({
        'status': 'not_analyzed',
        'message': 'No analysis available. Please trigger analysis first.'
    }), 404

# Note: The frontend calls POST /api/repos/:id/analyze
# We need to register this route in repos_bp or here but with matching path.
# Since we are using blueprints, let's add it to repos_bp in the repos.py file or import it there.
# Actually, let's put the logic here and import it in repos.py to keep it clean, 
# OR just define it here and register it to the app with the correct URL.
# The user asked for `routes/repos.py`, so I should probably put it there.
# But for cleaner separation, I'll put the logic here and expose it.
# Wait, the user's structure had `routes/repos.py`. I will add the analyze route to `routes/repos.py` 
# and use helper functions if needed. 
# Re-reading the prompt: "routes/repos.py". I will append the analyze route to `routes/repos.py`.
