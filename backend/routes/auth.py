from flask import Blueprint, request, jsonify, redirect
from services.github_service import exchange_code_for_token, get_github_user
from utils.jwt_utils import generate_token
import os

auth_bp = Blueprint('auth', __name__)
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:8080')
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')

# In-memory token store (replace with DB/Redis in production)
token_store = {}

@auth_bp.route('/github')
def github_login():
    redirect_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo,read:user,user:email"
    return redirect(redirect_url)

@auth_bp.route('/callback')
@auth_bp.route('/github/callback')
def github_callback():
    code = request.args.get('code')
    if not code:
        return redirect(f"{FRONTEND_URL}/auth/callback?error=no_code")
    
    try:
        access_token = exchange_code_for_token(code)
        if not access_token:
             return redirect(f"{FRONTEND_URL}/auth/callback?error=oauth_failed")

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
        
        return redirect(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")
    except Exception as e:
        print(f"OAuth Error: {e}")
        return redirect(f"{FRONTEND_URL}/auth/callback?error=oauth_error")

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
