from flask import Blueprint, request, jsonify, redirect
from services.github_service import exchange_code_for_token, get_github_user
from services.session_store import SessionStore
from utils.jwt_utils import generate_token
import os
import secrets
from urllib.parse import urlencode

auth_bp = Blueprint('auth', __name__)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8080')
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')

# DB-backed (not an in-memory dict) so a server restart doesn't log everyone out.
token_store = SessionStore()

@auth_bp.route('/github')
def github_login():
    # Bind the OAuth callback to the browser that initiated login.
    state = secrets.token_urlsafe(32)
    redirect_url = "https://github.com/login/oauth/authorize?" + urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "scope": "repo read:user user:email",
        "state": state,
    })
    response = redirect(redirect_url)
    response.set_cookie(
        "gitcat_oauth_state", state, httponly=True, samesite="Lax",
        secure=request.is_secure or os.getenv("OAUTH_COOKIE_SECURE") == "true",
        max_age=600, path="/api/auth",
    )
    return response

@auth_bp.route('/callback')
@auth_bp.route('/github/callback')
def github_callback():
    state = request.args.get("state", "")
    cookie_state = request.cookies.get("gitcat_oauth_state", "")
    # Clear even on failure to prevent state reuse.
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        response = redirect(f"{FRONTEND_URL}/auth/callback?error=invalid_state")
        response.delete_cookie("gitcat_oauth_state", path="/api/auth")
        return response
    code = request.args.get('code')
    if not code:
        response = redirect(f"{FRONTEND_URL}/auth/callback?error=no_code")
        response.delete_cookie("gitcat_oauth_state", path="/api/auth")
        return response
    
    try:
        access_token = exchange_code_for_token(code)
        if not access_token:
             response = redirect(f"{FRONTEND_URL}/auth/callback?error=oauth_failed")
             response.delete_cookie("gitcat_oauth_state", path="/api/auth")
             return response

        github_user = get_github_user(access_token)
        
        # Save user to database
        from services.db_service import save_user
        save_user(
            github_id=github_user['id'],
            username=github_user['login'],
            avatar_url=github_user.get('avatar_url'),
            email=github_user.get('email')
        )
        
        # Generate JWT
        jwt_token = generate_token(github_user['id'])
        
        # Store access token
        token_store[jwt_token] = access_token
        
        response = redirect(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")
        response.delete_cookie("gitcat_oauth_state", path="/api/auth")
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response
    except Exception as e:
        print(f"OAuth Error: {e}")
        response = redirect(f"{FRONTEND_URL}/auth/callback?error=oauth_error")
        response.delete_cookie("gitcat_oauth_state", path="/api/auth")
        return response

@auth_bp.route('/me')
def get_current_user():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = auth_header.split(" ")[1]
    github_token = token_store.get(token)
    
    if not github_token:
        return jsonify({'error': 'Invalid token'}), 401
        
    try:
        user = get_github_user(github_token)
        return jsonify(user)
    except:
        return jsonify({'error': 'Failed to fetch user'}), 500
