"""
Auth API Routes

Endpoints for user registration, login, logout, and session management.
Provides login_required decorator for protecting portfolio routes.
"""
import re
from functools import wraps
from flask import Blueprint, jsonify, request, session, g

from app.models.user import User

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator that requires an authenticated session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'error': 'Authentication required',
                'code': 'UNAUTHENTICATED'
            }), 401
        g.current_user_id = str(user_id)
        return f(*args, **kwargs)
    return decorated


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    POST /api/auth/register
    Create a new user account. Auto-logs in on success.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    # Validate username: 3-50 chars, alphanumeric + underscore
    if not username or len(username) < 3 or len(username) > 50:
        return jsonify({'error': 'Username must be 3-50 characters'}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username must be alphanumeric (underscores allowed)'}), 400

    # Validate password: 6+ chars
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Check if username already exists
    existing = User.get_by_username(username)
    if existing:
        return jsonify({'error': 'Username already taken'}), 409

    # Create user
    user = User.create(username, password)

    # Auto-login
    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({
        'message': 'Account created',
        'user': {'id': user['id'], 'username': user['username']}
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Verify credentials and create session.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = User.verify(username, password)
    if not user:
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']

    return jsonify({
        'message': 'Logged in',
        'user': {'id': user['id'], 'username': user['username']}
    })


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    POST /api/auth/logout
    Clear the session.
    """
    session.clear()
    return jsonify({'message': 'Logged out'})


@auth_bp.route('/me', methods=['GET'])
def me():
    """
    GET /api/auth/me
    Return current user from session, or 401.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated', 'code': 'UNAUTHENTICATED'}), 401

    return jsonify({
        'user': {
            'id': user_id,
            'username': session.get('username')
        }
    })
