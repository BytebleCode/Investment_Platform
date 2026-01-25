"""
Production Logging Configuration

Provides structured logging with rotation for production deployment.
Supports different log levels and formats for various environments.
"""
import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


class RequestFormatter(logging.Formatter):
    """Custom formatter that includes request context if available."""

    def format(self, record):
        try:
            from flask import request, has_request_context
            if has_request_context():
                record.url = request.url
                record.remote_addr = request.remote_addr
                record.method = request.method
            else:
                record.url = '-'
                record.remote_addr = '-'
                record.method = '-'
        except ImportError:
            record.url = '-'
            record.remote_addr = '-'
            record.method = '-'

        return super().format(record)


def setup_logging(app):
    """
    Configure application logging based on environment.

    Args:
        app: Flask application instance
    """
    # Get configuration from app or environment
    log_level = app.config.get('LOG_LEVEL', os.getenv('LOG_LEVEL', 'INFO'))
    log_dir = os.getenv('LOG_DIR', 'logs')
    is_production = os.getenv('FLASK_ENV') == 'production'

    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Clear any existing handlers
    app.logger.handlers.clear()

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    app.logger.setLevel(numeric_level)

    # Define formatters
    standard_format = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    detailed_format = RequestFormatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(remote_addr)s - %(method)s %(url)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    json_format = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
        '"message": "%(message)s", "module": "%(module)s", "line": %(lineno)d}'
    )

    if is_production:
        # Production: File-based rotating logs

        # Main application log (rotating by size)
        app_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        app_handler.setLevel(numeric_level)
        app_handler.setFormatter(detailed_format)
        app.logger.addHandler(app_handler)

        # Error log (separate file for errors only)
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, 'error.log'),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_format)
        app.logger.addHandler(error_handler)

        # Daily rotating log for audit trail
        audit_handler = TimedRotatingFileHandler(
            os.path.join(log_dir, 'audit.log'),
            when='midnight',
            interval=1,
            backupCount=30,  # Keep 30 days
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(json_format)
        app.logger.addHandler(audit_handler)

    else:
        # Development: Console output with colors

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        # Try to use colorful logging if available
        try:
            import colorlog
            color_format = colorlog.ColoredFormatter(
                '%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(name)s: %(message)s',
                datefmt='%H:%M:%S',
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
            console_handler.setFormatter(color_format)
        except ImportError:
            console_handler.setFormatter(standard_format)

        app.logger.addHandler(console_handler)

        # Also log to file in development (useful for debugging)
        dev_file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'development.log'),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        dev_file_handler.setLevel(logging.DEBUG)
        dev_file_handler.setFormatter(detailed_format)
        app.logger.addHandler(dev_file_handler)

    # Log startup message
    app.logger.info(f'Investment Platform logging initialized')
    app.logger.info(f'Log level: {log_level}')
    app.logger.info(f'Environment: {"production" if is_production else "development"}')


def setup_request_logging(app):
    """
    Set up request/response logging middleware.

    Args:
        app: Flask application instance
    """
    @app.before_request
    def log_request_info():
        """Log incoming request details."""
        from flask import request

        app.logger.debug(
            f'Request: {request.method} {request.path} '
            f'from {request.remote_addr}'
        )

        # Log request body for non-GET requests (be careful with sensitive data)
        if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
            # Sanitize sensitive fields
            data = request.get_json(silent=True) or {}
            sanitized = sanitize_log_data(data)
            app.logger.debug(f'Request body: {sanitized}')

    @app.after_request
    def log_response_info(response):
        """Log response details."""
        from flask import request

        app.logger.info(
            f'{request.method} {request.path} '
            f'- {response.status_code} '
            f'({response.content_length or 0} bytes)'
        )

        return response


def sanitize_log_data(data: dict) -> dict:
    """
    Remove sensitive fields from data before logging.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary safe for logging
    """
    sensitive_fields = {
        'password', 'pwd', 'secret', 'token', 'api_key',
        'apikey', 'auth', 'credential', 'ssn', 'credit_card'
    }

    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in sensitive_fields):
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value

    return sanitized


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the application configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # If no handlers, add a basic console handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class TradeLogger:
    """Specialized logger for trade operations (audit trail)."""

    def __init__(self, app=None):
        self.logger = logging.getLogger('trades')

        if app:
            log_dir = os.getenv('LOG_DIR', 'logs')
            handler = TimedRotatingFileHandler(
                os.path.join(log_dir, 'trades.log'),
                when='midnight',
                interval=1,
                backupCount=365,  # Keep 1 year of trade logs
                encoding='utf-8'
            )
            handler.setFormatter(logging.Formatter(
                '%(asctime)s|%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_trade(self, trade_data: dict):
        """Log a trade for audit purposes."""
        trade_str = (
            f"TRADE|{trade_data.get('trade_id')}|"
            f"{trade_data.get('type')}|{trade_data.get('symbol')}|"
            f"{trade_data.get('quantity')}|{trade_data.get('price')}|"
            f"{trade_data.get('total')}|{trade_data.get('user_id')}"
        )
        self.logger.info(trade_str)

    def log_auto_trade(self, trade_data: dict, strategy: str):
        """Log an auto-executed trade."""
        trade_str = (
            f"AUTO_TRADE|{trade_data.get('trade_id')}|{strategy}|"
            f"{trade_data.get('type')}|{trade_data.get('symbol')}|"
            f"{trade_data.get('quantity')}|{trade_data.get('price')}"
        )
        self.logger.info(trade_str)
