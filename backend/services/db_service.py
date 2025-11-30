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

    conn.commit()
    conn.close()

    db_location = f"PostgreSQL ({DB_HOST}:{DB_PORT}/{DB_NAME})" if DB_TYPE == 'postgresql' else DB_PATH
    print(f"✅ Database initialized at {db_location}")

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
    print(f"✅ Saved analysis for repo {repo_id} (user {github_user_id})")

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
