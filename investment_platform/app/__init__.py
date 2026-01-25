"""
Investment Platform - Flask Application Factory
"""
import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from app.database import init_db, create_all, close_session, get_scoped_session

# For backward compatibility - db.session can still be used
class DBCompat:
    """Compatibility layer for db.session usage."""

    @property
    def session(self):
        return get_scoped_session()

db = DBCompat()


def create_app(config_class=None):
    """
    Application factory pattern for Flask app.

    Args:
        config_class: Configuration class to use. Defaults to Config.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration
    if config_class is None:
        from app.config import Config
        config_class = Config
    # Instantiate config class so that @property decorators work
    app.config.from_object(config_class())

    # Initialize database
    init_db(app)

    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from app.api.portfolio_routes import portfolio_bp
    from app.api.holdings_routes import holdings_bp
    from app.api.trades_routes import trades_bp
    from app.api.strategy_routes import strategy_bp
    from app.api.market_data_routes import market_data_bp
    from app.api.trading_routes import trading_bp
    from app.api.health_routes import health_bp
    from app.api.backtest_routes import backtest_bp

    app.register_blueprint(portfolio_bp, url_prefix='/api/portfolio')
    app.register_blueprint(holdings_bp, url_prefix='/api/holdings')
    app.register_blueprint(trades_bp, url_prefix='/api/trades')
    app.register_blueprint(strategy_bp, url_prefix='/api/strategies')
    app.register_blueprint(market_data_bp, url_prefix='/api/market')
    app.register_blueprint(trading_bp, url_prefix='/api/trading')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(backtest_bp, url_prefix='/api/backtest')

    # Create database tables
    create_all()

    # Serve static HTML frontend
    static_folder = os.path.join(os.path.dirname(__file__), 'static')

    @app.route('/')
    def index():
        return send_from_directory(static_folder, 'index.html')

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(static_folder, filename)

    # Teardown - close session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_session()

    # Register error handlers
    register_error_handlers(app)

    # Setup logging
    setup_logging(app)

    return app


def register_error_handlers(app):
    """Register error handlers for common HTTP errors."""
    from flask import jsonify

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description)
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500


def setup_logging(app):
    """Configure application logging."""
    import logging
    from logging.handlers import RotatingFileHandler
    import os

    if not app.debug:
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/investment_platform.log',
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Investment Platform startup')
