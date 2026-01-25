"""
Security Module

Provides security utilities and middleware for the Investment Platform:
- Rate limiting
- CORS configuration
- Session security
- Input sanitization
- Security headers
"""
import os
import re
import html
from functools import wraps
from datetime import timedelta
from flask import Flask, request, jsonify, g
from flask_cors import CORS


def configure_security(app: Flask):
    """
    Configure all security settings for the application.

    Args:
        app: Flask application instance
    """
    configure_cors(app)
    configure_session_security(app)
    configure_security_headers(app)
    configure_rate_limiting(app)


def configure_cors(app: Flask):
    """
    Configure Cross-Origin Resource Sharing (CORS).

    Args:
        app: Flask application instance
    """
    is_production = os.getenv('FLASK_ENV') == 'production'

    if is_production:
        # Restrictive CORS for production
        allowed_origins = os.getenv('CORS_ORIGINS', '').split(',')
        allowed_origins = [o.strip() for o in allowed_origins if o.strip()]

        if not allowed_origins:
            app.logger.warning('No CORS_ORIGINS configured for production!')
            allowed_origins = []

        CORS(app, resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                "expose_headers": ["Content-Range", "X-Content-Range"],
                "supports_credentials": True,
                "max_age": 600  # Cache preflight for 10 minutes
            }
        })
    else:
        # Permissive CORS for development
        CORS(app, resources={
            r"/api/*": {
                "origins": "*",
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        })


def configure_session_security(app: Flask):
    """
    Configure secure session settings.

    Args:
        app: Flask application instance
    """
    is_production = os.getenv('FLASK_ENV') == 'production'

    app.config.update(
        SESSION_COOKIE_SECURE=is_production,  # HTTPS only in production
        SESSION_COOKIE_HTTPONLY=True,  # No JavaScript access
        SESSION_COOKIE_SAMESITE='Lax',  # CSRF protection
        PERMANENT_SESSION_LIFETIME=timedelta(hours=24),
        SESSION_REFRESH_EACH_REQUEST=True
    )

    if is_production:
        app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'


def configure_security_headers(app: Flask):
    """
    Add security headers to all responses.

    Args:
        app: Flask application instance
    """
    @app.after_request
    def add_security_headers(response):
        """Add security headers to response."""
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Enable XSS filter
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Content Security Policy (adjust based on your needs)
        if os.getenv('FLASK_ENV') == 'production':
            response.headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self';"
            )

        # Strict Transport Security (HTTPS enforcement)
        if os.getenv('FLASK_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = (
                'max-age=31536000; includeSubDomains'
            )

        return response


def configure_rate_limiting(app: Flask):
    """
    Configure rate limiting for API endpoints.

    Note: For production, consider using Flask-Limiter with Redis backend.
    This is a simple in-memory implementation for reference.

    Args:
        app: Flask application instance
    """
    if not os.getenv('RATELIMIT_ENABLED', 'True').lower() == 'true':
        return

    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"],
            storage_uri=os.getenv('RATELIMIT_STORAGE_URL', 'memory://'),
            strategy="fixed-window"
        )

        # Store limiter on app for use in routes
        app.limiter = limiter

        app.logger.info('Rate limiting enabled')

    except ImportError:
        app.logger.warning(
            'flask-limiter not installed. Rate limiting disabled. '
            'Install with: pip install flask-limiter'
        )
        app.limiter = None


def rate_limit(limit_string: str):
    """
    Decorator for rate limiting specific endpoints.

    Args:
        limit_string: Rate limit string (e.g., "5 per minute")

    Usage:
        @app.route('/api/expensive')
        @rate_limit("5 per minute")
        def expensive_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app
            if hasattr(current_app, 'limiter') and current_app.limiter:
                # Apply rate limit via Flask-Limiter
                return current_app.limiter.limit(limit_string)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sanitize_input(value: str) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return value

    # HTML entity encoding
    value = html.escape(value)

    # Remove potential SQL injection patterns
    # (SQLAlchemy ORM should handle this, but defense in depth)
    sql_patterns = [
        r'(\s|^)(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)(\s|$)',
        r'--',
        r';.*$',
        r'/\*.*\*/'
    ]
    for pattern in sql_patterns:
        value = re.sub(pattern, ' ', value, flags=re.IGNORECASE)

    # Remove null bytes
    value = value.replace('\x00', '')

    # Limit length
    max_length = 10000
    if len(value) > max_length:
        value = value[:max_length]

    return value.strip()


def sanitize_dict(data: dict) -> dict:
    """
    Recursively sanitize all string values in a dictionary.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Sanitize key
        san_key = sanitize_input(str(key)) if not isinstance(key, str) else sanitize_input(key)

        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[san_key] = sanitize_input(value)
        elif isinstance(value, dict):
            sanitized[san_key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[san_key] = [
                sanitize_dict(item) if isinstance(item, dict)
                else sanitize_input(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[san_key] = value

    return sanitized


def validate_user_id(user_id: str) -> bool:
    """
    Validate user ID format.

    Args:
        user_id: User ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not user_id:
        return False

    # User ID should be alphanumeric with underscores, max 50 chars
    pattern = r'^[a-zA-Z0-9_]{1,50}$'
    return bool(re.match(pattern, user_id))


def validate_symbol(symbol: str) -> bool:
    """
    Validate stock symbol format.

    Args:
        symbol: Stock symbol to validate

    Returns:
        True if valid, False otherwise
    """
    if not symbol:
        return False

    # Symbol should be uppercase alphanumeric with optional period, max 10 chars
    pattern = r'^[A-Z0-9\.]{1,10}$'
    return bool(re.match(pattern, symbol))


def require_json(f):
    """
    Decorator to ensure request has JSON content type.

    Usage:
        @app.route('/api/data', methods=['POST'])
        @require_json
        def handle_data():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'error': 'Content-Type must be application/json'
            }), 415
        return f(*args, **kwargs)
    return decorated_function


def get_client_ip() -> str:
    """
    Get client IP address, handling proxies.

    Returns:
        Client IP address string
    """
    # Check for forwarded headers (reverse proxy)
    if request.headers.get('X-Forwarded-For'):
        # Take the first IP in the chain
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


class SecurityMiddleware:
    """
    WSGI middleware for additional security checks.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Block requests with suspicious patterns
        path = environ.get('PATH_INFO', '')

        # Block path traversal attempts
        if '..' in path or '//' in path:
            start_response('400 Bad Request', [('Content-Type', 'text/plain')])
            return [b'Invalid request path']

        # Block common attack patterns
        suspicious_patterns = [
            '/etc/passwd',
            '/proc/self',
            'wp-admin',
            'phpmyadmin',
            '.git/',
            '.env'
        ]

        path_lower = path.lower()
        for pattern in suspicious_patterns:
            if pattern in path_lower:
                start_response('403 Forbidden', [('Content-Type', 'text/plain')])
                return [b'Access denied']

        return self.app(environ, start_response)
