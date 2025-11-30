from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Initialize database
    from services.db_service import init_database
    init_database()

    # Import routes
    from routes.auth import auth_bp
    from routes.repos import repos_bp
    from routes.chat import chat_bp

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(repos_bp, url_prefix='/api/repos')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    
    # Analysis route is part of repos but we might want a separate blueprint if it grows
    # For now, we'll keep analysis in repos or separate if needed. 
    # The plan mentioned /api/analysis/<id>, let's handle that in repos_bp or a new one.
    # Let's add a separate blueprint for analysis to be clean.
    from routes.analysis import analysis_bp
    app.register_blueprint(analysis_bp, url_prefix='/api/analysis')
    
    # Dashboard routes
    from routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'flask-backend'}

    return app

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    app = create_app()
    print(f"🚀 Flask Backend running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
