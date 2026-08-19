"""
Database service for persistent storage of analysis results.
Supports both SQLite (development) and PostgreSQL (production).
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor

# Determine database type from environment
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # 'sqlite' or 'postgresql'

if DB_TYPE == 'postgresql':
    DB_HOST = os.getenv('DB_HOST', 'db')
    DB_NAME = os.getenv('DB_NAME', 'gitpro')
    DB_USER = os.getenv('DB_USER', 'gitpro_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'gitpro_pass')
    DB_PORT = os.getenv('DB_PORT', 5432)
else:
    # Database file path for SQLite
    DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'gitpro.db')

def get_db_connection():
    """Get a database connection based on environment configuration."""
    if DB_TYPE == 'postgresql':
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        conn.cursor_factory = RealDictCursor  # Return rows as dictionaries
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return conn

def init_database():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        # Create users table for PostgreSQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                github_id BIGINT PRIMARY KEY,
                username TEXT NOT NULL,
                avatar_url TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create analysis_results table for PostgreSQL
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id SERIAL PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                github_user_id BIGINT NOT NULL,
                repo_name TEXT,
                repo_full_name TEXT,
                analysis_text TEXT,
                kpis TEXT,
                anomalies TEXT,
                generated_at TIMESTAMP,
                status TEXT,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id),
                UNIQUE(repo_id, github_user_id)
            )
        ''')

        # Append-only log of every analysis run (analysis_results only keeps the latest per
        # repo/user) — this is what powers the health-score trend chart.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id SERIAL PRIMARY KEY,
                repo_id INTEGER NOT NULL,
                github_user_id BIGINT NOT NULL,
                generated_at TIMESTAMP,
                grade TEXT,
                overall_health_score REAL,
                quality_score REAL,
                maintainability_index REAL,
                productivity_score REAL,
                security_risk_score REAL,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id)
            )
        ''')

        # Repos with auto-review enabled: every new/updated PR gets an automatic
        # AI review posted as a comment via a GitHub webhook.
        # NOTE (dev-grade security): github_token is stored in plaintext here so the
        # webhook handler can act without an active browser session. Encrypt at rest
        # before using this against real private repos in anything beyond local dev.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_reviews (
                repo_id BIGINT PRIMARY KEY,
                github_user_id BIGINT NOT NULL,
                repo_full_name TEXT NOT NULL,
                github_token TEXT NOT NULL,
                webhook_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id)
            )
        ''')

        # Repos opted in to a public, no-auth "shareable card" of their latest analysis.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS public_shares (
                repo_id BIGINT PRIMARY KEY,
                github_user_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id)
            )
        ''')

        # Maps an issued app JWT to the raw GitHub access token it represents. DB-backed
        # (not an in-memory dict) so a server restart doesn't silently log everyone out —
        # important once this isn't just running on localhost for one person.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                jwt_token TEXT PRIMARY KEY,
                github_access_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    else:
        # Create users table for SQLite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                github_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                avatar_url TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create analysis_results table for SQLite
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                github_user_id INTEGER NOT NULL,
                repo_name TEXT,
                repo_full_name TEXT,
                analysis_text TEXT,
                kpis TEXT,
                anomalies TEXT,
                generated_at TIMESTAMP,
                status TEXT,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id),
                UNIQUE(repo_id, github_user_id)
            )
        ''')

        # Append-only log of every analysis run (analysis_results only keeps the latest per
        # repo/user) — this is what powers the health-score trend chart.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                github_user_id INTEGER NOT NULL,
                generated_at TIMESTAMP,
                grade TEXT,
                overall_health_score REAL,
                quality_score REAL,
                maintainability_index REAL,
                productivity_score REAL,
                security_risk_score REAL,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id)
            )
        ''')

        # Repos with auto-review enabled: every new/updated PR gets an automatic
        # AI review posted as a comment via a GitHub webhook.
        # NOTE (dev-grade security): github_token is stored in plaintext here so the
        # webhook handler can act without an active browser session. Encrypt at rest
        # before using this against real private repos in anything beyond local dev.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_reviews (
                repo_id INTEGER PRIMARY KEY,
                github_user_id INTEGER NOT NULL,
                repo_full_name TEXT NOT NULL,
                github_token TEXT NOT NULL,
                webhook_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id)
            )
        ''')

        # Repos opted in to a public, no-auth "shareable card" of their latest analysis.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS public_shares (
                repo_id INTEGER PRIMARY KEY,
                github_user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (github_user_id) REFERENCES users(github_id)
            )
        ''')

        # Maps an issued app JWT to the raw GitHub access token it represents. DB-backed
        # (not an in-memory dict) so a server restart doesn't silently log everyone out —
        # important once this isn't just running on localhost for one person.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                jwt_token TEXT PRIMARY KEY,
                github_access_token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    conn.commit()
    conn.close()

    db_location = f"PostgreSQL ({DB_HOST}:{DB_PORT}/{DB_NAME})" if DB_TYPE == 'postgresql' else DB_PATH
    print(f"Database initialized at {db_location}")

def save_user(github_id: int, username: str, avatar_url: str = None, email: str = None):
    """Save or update user information."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO users (github_id, username, avatar_url, email)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (github_id) DO UPDATE SET
                username = EXCLUDED.username,
                avatar_url = EXCLUDED.avatar_url,
                email = EXCLUDED.email
        ''', (github_id, username, avatar_url, email))
    else:
        cursor.execute('''
            INSERT INTO users (github_id, username, avatar_url, email)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(github_id) DO UPDATE SET
                username = excluded.username,
                avatar_url = excluded.avatar_url,
                email = excluded.email
        ''', (github_id, username, avatar_url, email))

    conn.commit()
    conn.close()

def get_user(github_id: int) -> Optional[Dict[str, Any]]:
    """Get user by GitHub ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM users WHERE github_id = %s', (github_id,))
    else:
        cursor.execute('SELECT * FROM users WHERE github_id = ?', (github_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None

def save_session(jwt_token: str, github_access_token: str):
    """Records that jwt_token represents github_access_token, replacing any prior mapping."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO sessions (jwt_token, github_access_token)
            VALUES (%s, %s)
            ON CONFLICT (jwt_token) DO UPDATE SET github_access_token = EXCLUDED.github_access_token
        ''', (jwt_token, github_access_token))
    else:
        cursor.execute('''
            INSERT INTO sessions (jwt_token, github_access_token)
            VALUES (?, ?)
            ON CONFLICT(jwt_token) DO UPDATE SET github_access_token = excluded.github_access_token
        ''', (jwt_token, github_access_token))

    conn.commit()
    conn.close()

def get_session(jwt_token: str) -> Optional[str]:
    """Returns the GitHub access token for a JWT, or None if it isn't a known session."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT github_access_token FROM sessions WHERE jwt_token = %s', (jwt_token,))
    else:
        cursor.execute('SELECT github_access_token FROM sessions WHERE jwt_token = ?', (jwt_token,))

    row = cursor.fetchone()
    conn.close()
    return row['github_access_token'] if row else None

def save_analysis(repo_id: int, github_user_id: int, analysis_data: Dict[str, Any]):
    """
    Save or update analysis results for a repository and user.

    Args:
        repo_id: GitHub repository ID
        github_user_id: GitHub user ID
        analysis_data: Dictionary containing analysis, kpis, anomalies, etc.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Extract data
    repo_name = analysis_data.get('repo_name', '')
    repo_full_name = analysis_data.get('repo_full_name', '')
    analysis_text = analysis_data.get('analysis', '')
    kpis = json.dumps(analysis_data.get('kpis', {}))
    anomalies = json.dumps(analysis_data.get('anomalies', []))
    generated_at = analysis_data.get('generated_at', datetime.utcnow().isoformat())
    status = analysis_data.get('status', 'completed')

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO analysis_results
            (repo_id, github_user_id, repo_name, repo_full_name, analysis_text, kpis, anomalies, generated_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (repo_id, github_user_id) DO UPDATE SET
                repo_name = EXCLUDED.repo_name,
                repo_full_name = EXCLUDED.repo_full_name,
                analysis_text = EXCLUDED.analysis_text,
                kpis = EXCLUDED.kpis,
                anomalies = EXCLUDED.anomalies,
                generated_at = EXCLUDED.generated_at,
                status = EXCLUDED.status
        ''', (repo_id, github_user_id, repo_name, repo_full_name, analysis_text, kpis, anomalies, generated_at, status))
    else:
        cursor.execute('''
            INSERT INTO analysis_results
            (repo_id, github_user_id, repo_name, repo_full_name, analysis_text, kpis, anomalies, generated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo_id, github_user_id) DO UPDATE SET
                repo_name = excluded.repo_name,
                repo_full_name = excluded.repo_full_name,
                analysis_text = excluded.analysis_text,
                kpis = excluded.kpis,
                anomalies = excluded.anomalies,
                generated_at = excluded.generated_at,
                status = excluded.status
        ''', (repo_id, github_user_id, repo_name, repo_full_name, analysis_text, kpis, anomalies, generated_at, status))

    conn.commit()
    conn.close()
    print(f"Saved analysis for repo {repo_id} (user {github_user_id})")

def save_analysis_history(repo_id: int, github_user_id: int, analysis_data: Dict[str, Any]):
    """
    Appends a snapshot of this run's headline scores to analysis_history — unlike
    save_analysis, this never overwrites a previous row, so it's what the trend chart reads.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    kpis = analysis_data.get('kpis', {}) or {}
    summary = kpis.get('summary', {}) or {}
    quality = kpis.get('quality', {}) or {}
    maintainability = kpis.get('maintainability', {}) or {}
    productivity = kpis.get('productivity', {}) or {}
    security = kpis.get('security', {}) or {}
    generated_at = analysis_data.get('generated_at', datetime.utcnow().isoformat())

    values = (
        repo_id, github_user_id, generated_at,
        summary.get('grade'), summary.get('overall_health_score'),
        quality.get('quality_score'), maintainability.get('maintainability_index'),
        productivity.get('productivity_score'), security.get('risk_score'),
    )

    placeholder = '%s' if DB_TYPE == 'postgresql' else '?'
    cursor.execute(f'''
        INSERT INTO analysis_history
        (repo_id, github_user_id, generated_at, grade, overall_health_score,
         quality_score, maintainability_index, productivity_score, security_risk_score)
        VALUES ({', '.join([placeholder] * 9)})
    ''', values)

    conn.commit()
    conn.close()

def get_analysis_history(repo_id: int, github_user_id: int, limit: int = 60) -> List[Dict[str, Any]]:
    """Returns analysis runs for a repo, oldest first, for charting a trend over time."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT generated_at, grade, overall_health_score, quality_score,
                   maintainability_index, productivity_score, security_risk_score
            FROM analysis_history
            WHERE repo_id = %s AND github_user_id = %s
            ORDER BY generated_at DESC
            LIMIT %s
        ''', (repo_id, github_user_id, limit))
    else:
        cursor.execute('''
            SELECT generated_at, grade, overall_health_score, quality_score,
                   maintainability_index, productivity_score, security_risk_score
            FROM analysis_history
            WHERE repo_id = ? AND github_user_id = ?
            ORDER BY generated_at DESC
            LIMIT ?
        ''', (repo_id, github_user_id, limit))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    rows.reverse()  # oldest first, for left-to-right charting
    return rows

def get_analysis(repo_id: int, github_user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get analysis results for a repository and user.

    Args:
        repo_id: GitHub repository ID
        github_user_id: GitHub user ID

    Returns:
        Dictionary with analysis data or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM analysis_results
            WHERE repo_id = %s AND github_user_id = %s
        ''', (repo_id, github_user_id))
    else:
        cursor.execute('''
            SELECT * FROM analysis_results
            WHERE repo_id = ? AND github_user_id = ?
        ''', (repo_id, github_user_id))

    row = cursor.fetchone()
    conn.close()

    if row:
        data = dict(row)
        # Parse JSON fields
        data['kpis'] = json.loads(data['kpis']) if data['kpis'] else {}
        data['anomalies'] = json.loads(data['anomalies']) if data['anomalies'] else []
        # Rename for consistency with API
        data['analysis'] = data.pop('analysis_text')
        return data

    return None

def get_user_analyses(github_user_id: int) -> List[Dict[str, Any]]:
    """Get all analysis results for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            SELECT * FROM analysis_results
            WHERE github_user_id = %s
            ORDER BY generated_at DESC
        ''', (github_user_id,))
    else:
        cursor.execute('''
            SELECT * FROM analysis_results
            WHERE github_user_id = ?
            ORDER BY generated_at DESC
        ''', (github_user_id,))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        data = dict(row)
        data['kpis'] = json.loads(data['kpis']) if data['kpis'] else {}
        data['anomalies'] = json.loads(data['anomalies']) if data['anomalies'] else []
        data['analysis'] = data.pop('analysis_text')
        results.append(data)

    return results

def enable_auto_review(repo_id: int, github_user_id: int, repo_full_name: str, github_token: str, webhook_id: Optional[int]):
    """Marks a repo as having auto-review enabled, replacing any previous config for it."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO auto_reviews (repo_id, github_user_id, repo_full_name, github_token, webhook_id)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (repo_id) DO UPDATE SET
                github_user_id = EXCLUDED.github_user_id,
                repo_full_name = EXCLUDED.repo_full_name,
                github_token = EXCLUDED.github_token,
                webhook_id = EXCLUDED.webhook_id
        ''', (repo_id, github_user_id, repo_full_name, github_token, webhook_id))
    else:
        cursor.execute('''
            INSERT INTO auto_reviews (repo_id, github_user_id, repo_full_name, github_token, webhook_id)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET
                github_user_id = excluded.github_user_id,
                repo_full_name = excluded.repo_full_name,
                github_token = excluded.github_token,
                webhook_id = excluded.webhook_id
        ''', (repo_id, github_user_id, repo_full_name, github_token, webhook_id))

    conn.commit()
    conn.close()

def get_auto_review(repo_id: int) -> Optional[Dict[str, Any]]:
    """Returns the auto-review config for a repo, or None if not enabled."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM auto_reviews WHERE repo_id = %s', (repo_id,))
    else:
        cursor.execute('SELECT * FROM auto_reviews WHERE repo_id = ?', (repo_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def disable_auto_review(repo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('DELETE FROM auto_reviews WHERE repo_id = %s', (repo_id,))
    else:
        cursor.execute('DELETE FROM auto_reviews WHERE repo_id = ?', (repo_id,))

    conn.commit()
    conn.close()

def enable_share(repo_id: int, github_user_id: int):
    """Opts a repo in to its public shareable card, replacing any previous owner for it."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            INSERT INTO public_shares (repo_id, github_user_id)
            VALUES (%s, %s)
            ON CONFLICT (repo_id) DO UPDATE SET github_user_id = EXCLUDED.github_user_id
        ''', (repo_id, github_user_id))
    else:
        cursor.execute('''
            INSERT INTO public_shares (repo_id, github_user_id)
            VALUES (?, ?)
            ON CONFLICT(repo_id) DO UPDATE SET github_user_id = excluded.github_user_id
        ''', (repo_id, github_user_id))

    conn.commit()
    conn.close()

def get_share(repo_id: int) -> Optional[Dict[str, Any]]:
    """Returns the share config for a repo, or None if it isn't publicly shared."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('SELECT * FROM public_shares WHERE repo_id = %s', (repo_id,))
    else:
        cursor.execute('SELECT * FROM public_shares WHERE repo_id = ?', (repo_id,))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def disable_share(repo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('DELETE FROM public_shares WHERE repo_id = %s', (repo_id,))
    else:
        cursor.execute('DELETE FROM public_shares WHERE repo_id = ?', (repo_id,))

    conn.commit()
    conn.close()

def delete_analysis(repo_id: int, github_user_id: int):
    """Delete analysis results for a repository and user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if DB_TYPE == 'postgresql':
        cursor.execute('''
            DELETE FROM analysis_results
            WHERE repo_id = %s AND github_user_id = %s
        ''', (repo_id, github_user_id))
    else:
        cursor.execute('''
            DELETE FROM analysis_results
            WHERE repo_id = ? AND github_user_id = ?
        ''', (repo_id, github_user_id))

    conn.commit()
    conn.close()
